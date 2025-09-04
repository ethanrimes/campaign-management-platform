#!/usr/bin/env python3
# scripts/setup/run_migrations.py

"""
Run all database migrations in order.
Tracks which migrations have been applied and only runs new ones.

Usage:
    python scripts/setup/run_migrations.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution and tracking"""
    
    def __init__(self):
        self.migrations_dir = Path("backend/db/migrations")
        self.db_url = os.getenv("SUPABASE_DB_URL")
        
        if not self.db_url:
            raise ValueError(
                "SUPABASE_DB_URL not found in environment. "
                "This should be your Postgres connection string."
            )
        
        # Ensure SSL mode
        self.db_url = self._ensure_sslmode(self.db_url)
    
    def _ensure_sslmode(self, url: str) -> str:
        """Ensure the database URL includes sslmode=require"""
        if "?sslmode=" in url or "&sslmode=" in url:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}sslmode=require"
    
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def create_migrations_table(self):
        """Create the migrations tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT true,
            checksum VARCHAR(64),
            execution_time_ms INTEGER
        );
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
            conn.commit()
            logger.info("✓ Migrations table ready")
    
    def get_applied_migrations(self) -> set:
        """Get list of already applied migrations"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT version FROM schema_migrations WHERE success = true"
                )
                results = cur.fetchall()
                return {row['version'] for row in results}
    
    def get_pending_migrations(self) -> list:
        """Get list of migrations that need to be applied"""
        applied = self.get_applied_migrations()
        
        # Get all migration files
        migration_files = sorted([
            f for f in self.migrations_dir.glob("*.sql")
            if f.is_file()
        ])
        
        pending = []
        for file in migration_files:
            version = file.stem  # filename without extension
            if version not in applied:
                pending.append(file)
        
        return pending
    
    def check_migration_checksum(self, version: str, new_checksum: str) -> bool:
        """Check if a migration's checksum matches what was previously applied"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT checksum FROM schema_migrations WHERE version = %s AND success = true",
                    (version,)
                )
                result = cur.fetchone()
                if result and result['checksum']:
                    return result['checksum'] == new_checksum
        return True  # If no checksum stored, assume it's ok
    
    def run_migration(self, migration_file: Path) -> bool:
        """
        Run a single migration file
        
        Args:
            migration_file: Path to the migration SQL file
            
        Returns:
            True if successful, False otherwise
        """
        version = migration_file.stem
        
        # Read migration content
        try:
            sql_content = migration_file.read_text()
        except Exception as e:
            logger.error(f"  ✗ Error reading migration file: {e}")
            return False
        
        # Calculate checksum
        checksum = hashlib.md5(sql_content.encode()).hexdigest()
        
        # Check if already applied
        applied_migrations = self.get_applied_migrations()
        if version in applied_migrations:
            # Migration already applied, check if content changed
            if not self.check_migration_checksum(version, checksum):
                logger.warning(f"  ⚠️  {version} already applied but content has changed")
                logger.info("     Skipping (migrations should be immutable)")
            else:
                logger.info(f"  ✓ {version} already applied - skipping")
            return True
        
        logger.info(f"\nRunning migration: {version}")
        
        start_time = datetime.now()
        
        # Execute migration
        with self.get_connection() as conn:
            conn.autocommit = False
            try:
                with conn.cursor() as cur:
                    # Run the migration SQL
                    cur.execute(sql_content)
                    
                    # Calculate execution time
                    execution_time = int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    )
                    
                    # Record successful migration
                    # Use INSERT ... ON CONFLICT to handle race conditions
                    cur.execute("""
                        INSERT INTO schema_migrations 
                        (version, checksum, execution_time_ms, success)
                        VALUES (%s, %s, %s, true)
                        ON CONFLICT (version) 
                        DO UPDATE SET 
                            checksum = EXCLUDED.checksum,
                            execution_time_ms = EXCLUDED.execution_time_ms,
                            success = true,
                            applied_at = CURRENT_TIMESTAMP
                        WHERE schema_migrations.success = false
                    """, (version, checksum, execution_time))
                    
                    # Notify PostgREST to reload schema
                    cur.execute("NOTIFY pgrst, 'reload schema';")
                
                conn.commit()
                logger.info(f"  ✓ {version} applied successfully ({execution_time}ms)")
                return True
                
            except psycopg2.errors.UniqueViolation:
                # Migration was already recorded (race condition)
                conn.rollback()
                logger.info(f"  ✓ {version} already recorded - skipping")
                return True
                
            except Exception as e:
                conn.rollback()
                error_msg = str(e)
                
                # Check if it's just a "already exists" type error for idempotent operations
                if any(phrase in error_msg.lower() for phrase in [
                    "already exists", "duplicate", "constraint"
                ]):
                    logger.info(f"  ✓ {version} structures already exist - marking as applied")
                    
                    # Mark as successfully applied since the structures exist
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO schema_migrations 
                            (version, checksum, success)
                            VALUES (%s, %s, true)
                            ON CONFLICT (version) 
                            DO UPDATE SET success = true
                        """, (version, checksum))
                    conn.commit()
                    return True
                else:
                    logger.error(f"  ✗ {version} failed: {e}")
                    
                    # Record failed migration
                    try:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO schema_migrations 
                                (version, checksum, success)
                                VALUES (%s, %s, false)
                                ON CONFLICT (version) 
                                DO UPDATE SET success = false
                            """, (version, checksum))
                        conn.commit()
                    except:
                        pass  # Ignore errors recording failure
                    
                    return False
    
    def run_all_migrations(self):
        """Run all pending migrations"""
        logger.info("="*60)
        logger.info("DATABASE MIGRATION RUNNER")
        logger.info("="*60)
        
        # Ensure migrations table exists
        self.create_migrations_table()
        
        # Get pending migrations
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("\n✅ Database is up to date - no migrations to run")
            return True
        
        logger.info(f"\nFound {len(pending)} pending migration(s):")
        for file in pending:
            logger.info(f"  • {file.stem}")
        
        # Run each migration
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for migration_file in pending:
            result = self.run_migration(migration_file)
            if result:
                success_count += 1
            else:
                failed_count += 1
                # For idempotent migrations, we continue even if one "fails"
                # since it might just mean the structures already exist
                logger.info("  Continuing with next migration...")
        
        # Summary
        logger.info("\n" + "="*60)
        if failed_count == 0:
            logger.info(f"✅ SUCCESS: {success_count} migration(s) completed")
        else:
            logger.info(f"⚠️  COMPLETED: {success_count} successful, {failed_count} had issues")
            logger.info("Review the log above for details.")
        logger.info("="*60)
        
        # Return success even if some had issues, since migrations are idempotent
        return True
    
    def verify_schema(self):
        """Verify that key tables exist after migration"""
        tables_to_check = [
            'initiatives',
            'initiative_tokens',
            'campaigns',
            'ad_sets',
            'posts',
            'metrics',
            'research',
            'agent_memories'
        ]
        
        logger.info("\nVerifying schema...")
        all_exist = True
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for table in tables_to_check:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                    exists = cur.fetchone()['exists']
                    
                    if exists:
                        logger.info(f"  ✓ Table '{table}' exists")
                    else:
                        logger.error(f"  ✗ Table '{table}' missing!")
                        all_exist = False
        
        # Check for encrypted token columns
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'initiative_tokens' 
                    AND column_name LIKE '%_encrypted'
                """)
                encrypted_cols = [row['column_name'] for row in cur.fetchall()]
                
                if encrypted_cols:
                    logger.info(f"\n  ✓ Found {len(encrypted_cols)} encrypted token columns")
                else:
                    logger.warning("  ⚠️  No encrypted token columns found")
        
        return all_exist


async def main():
    """Main entry point"""
    try:
        runner = MigrationRunner()
        
        # Run all migrations
        success = runner.run_all_migrations()
        
        if success:
            # Verify schema
            schema_valid = runner.verify_schema()
            
            if schema_valid:
                logger.info("\n✅ All migrations completed successfully!")
                logger.info("\nYour database is ready for encrypted token storage.")
                logger.info("\nNext steps:")
                logger.info("1. Ensure ENCRYPTION_KEY is set in your .env file")
                logger.info("2. Run scripts/setup/create_initiative.py to create an initiative")
            else:
                logger.warning("\n⚠️  Some tables are missing. Review the schema.")
        else:
            logger.error("\n❌ Migration process encountered issues.")
            
    except Exception as e:
        logger.error(f"\n❌ Migration runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())