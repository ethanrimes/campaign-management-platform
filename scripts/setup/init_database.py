# scripts/setup/init_database.py

import asyncio
import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log loaded environment variables
logger.info("Loaded environment variables:")
logger.info(f"SUPABASE_URL={os.getenv('SUPABASE_URL')}")
logger.info(f"SUPABASE_DB_URL set={bool(os.getenv('SUPABASE_DB_URL'))}")
if os.getenv('SUPABASE_KEY'):
    logger.info(f"SUPABASE_KEY={os.getenv('SUPABASE_KEY')[:6]}... (truncated)")  # avoid leaking full key
if os.getenv('SUPABASE_SERVICE_KEY'):
    logger.info(f"SUPABASE_SERVICE_KEY={os.getenv('SUPABASE_SERVICE_KEY')[:6]}... (truncated)")


async def init_database():
    """Initialize database with schema and refresh PostgREST schema cache."""
    try:
        # --- Load & validate inputs -------------------------------------------------
        migration_file = Path("backend/db/migrations/001_initial_schema.sql")
        if not migration_file.exists():
            logger.error("Migration file not found at backend/db/migrations/001_initial_schema.sql")
            return False

        sql_content = migration_file.read_text()
        logger.info("Database initialization SQL loaded")

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        db_url = os.getenv("SUPABASE_DB_URL")

        if not db_url:
            logger.error("SUPABASE_DB_URL not found - needed to apply migrations")
            return False
        if not supabase_url or not supabase_service_key:
            logger.error("Supabase REST credentials not found (SUPABASE_URL / SUPABASE_SERVICE_KEY)")
            return False
        if supabase_url.startswith("postgres://"):
            logger.error(
                "SUPABASE_URL appears to be a Postgres connection string. "
                "Use https://<project>.supabase.co for SUPABASE_URL and put the Postgres URI in SUPABASE_DB_URL."
            )
            return False

        # --- Normalize DB URL: ensure sslmode=require ------------------------------
        # Works whether URL already has query string or not.
        def ensure_sslmode_require(url: str) -> str:
            if "?sslmode=" in url or "&sslmode=" in url:
                return url  # user supplied an explicit sslmode
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}sslmode=require"

        db_url_final = ensure_sslmode_require(db_url)

        # --- Apply migration via psycopg2 ------------------------------------------
        try:
            import psycopg2

            logger.info("Applying database migration...")
            conn = psycopg2.connect(db_url_final, connect_timeout=15)
            conn.autocommit = True  # make DDL + NOTIFY visible immediately
            with conn.cursor() as cur:
                cur.execute(sql_content)
                # Tell PostgREST to refresh its schema cache so REST can see new tables
                cur.execute("NOTIFY pgrst, 'reload schema';")
            conn.close()
            logger.info("Database migration applied successfully and schema reload notified")
        except Exception as e:
            logger.error(f"Failed to apply migration: {e}")
            return False

        # --- Verify via REST (with a brief retry after NOTIFY) ---------------------
        client = create_client(supabase_url, supabase_service_key)

        def try_rest_once():
            # Use a very light query; empty tables will still return 200
            return client.table("initiatives").select("id").limit(1).execute()

        # Short retry loop in case the schema cache takes a moment to refresh
        import time
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                _ = try_rest_once()
                logger.info("Supabase REST API connection successful")
                break
            except Exception as e:
                msg = str(e)
                if "PGRST205" in msg or "Could not find the table" in msg:
                    if attempt < max_attempts:
                        wait = 0.5 * attempt  # 0.5s, 1.0s, 1.5s...
                        logger.info(f"Schema not visible yet (attempt {attempt}/{max_attempts}); retrying in {wait:.1f}s...")
                        time.sleep(wait)
                        continue
                logger.error(f"Supabase REST API connection failed: {e}")
                return False

        # --- Optional: quick direct DB sanity check --------------------------------
        try:
            import psycopg2
            conn = psycopg2.connect(db_url_final, connect_timeout=10)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM public.initiatives LIMIT 1;")
                _ = cur.fetchone()  # ignore result; exists -> query OK (0 rows also OK)
            conn.close()
            logger.info("Direct Postgres sanity check successful")
        except Exception as e:
            logger.warning(f"Direct Postgres sanity check encountered an issue (continuing): {e}")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(init_database())