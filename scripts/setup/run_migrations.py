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
import re

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
    
    def split_sql_statements(self, sql_content: str) -> list:
        """
        Split SQL content into individual statements.
        This handles DO $$ blocks and other multi-line statements properly.
        """
        # Remove comments
        sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        
        # Split by semicolon, but not within DO blocks or strings
        statements = []
        current_statement = []
        in_do_block = False
        in_string = False
        escape_next = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Track DO blocks
            if 'DO $$' in line:
                in_do_block = True
            elif '$$;' in line and in_do_block:
                in_do_block = False
                current_statement.append(line)
                statements.append('\n'.join(current_statement))
                current_statement = []
                continue
            
            # For regular statements
            if not in_do_block and line.endswith(';'):
                current_statement.append(line)
                statements.append('\n'.join(current_statement))
                current_statement = []
            else:
                current_statement.append(line)
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return [s.strip() for s in statements if s.strip()]
    
    def run_migration(self, migration_file: Path) -> bool:
        """
        Run a single migration file statement by statement
        
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
            if not self.check_migration_checksum(version, checksum):
                logger.warning(f"  ⚠️  {version} already applied but content has changed")
                logger.info("     Consider creating a new migration file for changes")
            else:
                logger.info(f"  ✓ {version} already applied - skipping")
            return True
        
        logger.info(f"\nRunning migration: {version}")
        
        start_time = datetime.now()
        errors_encountered = []
        statements_applied = 0
        statements_skipped = 0
        
        # Split into individual statements and run each
        statements = self.split_sql_statements(sql_content)
        total_statements = len(statements)
        
        with self.get_connection() as conn:
            for i, statement in enumerate(statements, 1):
                if not statement.strip():
                    continue
                    
                try:
                    with conn.cursor() as cur:
                        cur.execute(statement)
                        conn.commit()
                        statements_applied += 1
                        
                except psycopg2.errors.DuplicateTable as e:
                    conn.rollback()
                    statements_skipped += 1
                    logger.debug(f"    Table already exists (statement {i}/{total_statements})")
                    
                except psycopg2.errors.DuplicateObject as e:
                    conn.rollback()
                    statements_skipped += 1
                    logger.debug(f"    Object already exists (statement {i}/{total_statements})")
                    
                except psycopg2.errors.DuplicateColumn as e:
                    conn.rollback()
                    statements_skipped += 1
                    logger.debug(f"    Column already exists (statement {i}/{total_statements})")
                    
                except psycopg2.errors.UniqueViolation as e:
                    conn.rollback()
                    statements_skipped += 1
                    logger.debug(f"    Constraint already exists (statement {i}/{total_statements})")
                    
                except Exception as e:
                    conn.rollback()
                    error_msg = str(e)
                    
                    # Check if it's an ignorable error
                    if any(phrase in error_msg.lower() for phrase in [
                        "already exists", "duplicate", "multiple primary keys"
                    ]):
                        statements_skipped += 1
                        logger.debug(f"    Skipping (statement {i}/{total_statements}): {error_msg[:100]}")
                    else:
                        errors_encountered.append(f"Statement {i}: {error_msg}")
                        logger.error(f"    ✗ Error in statement {i}/{total_statements}: {error_msg}")
            
            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            
            # Determine if migration was successful
            success = len(errors_encountered) == 0 and (statements_applied > 0 or statements_skipped > 0)
            
            if success:
                # Record successful migration
                with conn.cursor() as cur:
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
                    """, (version, checksum, execution_time))
                    
                    # Notify PostgREST to reload schema
                    cur.execute("NOTIFY pgrst, 'reload schema';")
                
                conn.commit()
                
                logger.info(f"  ✓ {version} completed successfully")
                logger.info(f"    Applied: {statements_applied} statements, Skipped: {statements_skipped} statements")
                logger.info(f"    Time: {execution_time}ms")
                return True
            else:
                logger.error(f"  ✗ {version} failed with {len(errors_encountered)} errors")
                for error in errors_encountered[:5]:  # Show first 5 errors
                    logger.error(f"    - {error}")
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
        
        for migration_file in pending:
            result = self.run_migration(migration_file)
            if result:
                success_count += 1
            else:
                failed_count += 1
                # Stop on first failure for safety
                logger.error("Stopping migration process due to failure")
                break
        
        # Summary
        logger.info("\n" + "="*60)
        if failed_count == 0:
            logger.info(f"✅ SUCCESS: {success_count} migration(s) completed")
        else:
            logger.error(f"⚠️  PARTIAL: {success_count} successful, {failed_count} failed")
            logger.info("Fix the failed migration and run again.")
        logger.info("="*60)
        
        return failed_count == 0
    
    def verify_schema(self):
        """Verify that key tables and columns exist after migration"""
        logger.info("\nVerifying schema...")
        all_valid = True
        
        # Check tables
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
                        all_valid = False
        
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
                    for col in encrypted_cols:
                        logger.debug(f"    - {col}")
                else:
                    logger.warning("  ⚠️  No encrypted token columns found")
                    all_valid = False
        
        # Check for initiative_id in all dependent tables
        tables_needing_initiative_id = ['ad_sets', 'posts', 'metrics', 'agent_memories']
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for table in tables_needing_initiative_id:
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        AND column_name = 'initiative_id'
                    """, (table,))
                    
                    if cur.fetchone():
                        logger.info(f"  ✓ Table '{table}' has initiative_id column")
                    else:
                        logger.error(f"  ✗ Table '{table}' missing initiative_id column!")
                        all_valid = False
        
        return all_valid


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
                logger.info("\n✅ All migrations completed and schema verified!")
                logger.info("\nYour database is ready for use.")
                logger.info("\nNext steps:")
                logger.info("1. Ensure ENCRYPTION_KEY is set in your .env file")
                logger.info("2. Run scripts/setup/create_initiative.py to create an initiative")
            else:
                logger.warning("\n⚠️  Schema validation found issues. Review the output above.")
        else:
            logger.error("\n✗ Migration process failed. Please fix errors and run again.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n✗ Migration runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())