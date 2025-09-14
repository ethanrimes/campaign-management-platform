# scripts/setup/create_storage_bucket.py

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(f"Path: {str(Path(__file__).parent.parent.parent)}")

import os
import asyncio
from supabase import create_client
from backend.config.settings import settings
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


async def create_storage_bucket():
    """Create the generated-media storage bucket in Supabase"""
    
    # Use service key for admin access (bypasses RLS)
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY  # Service key has admin privileges
    )
    
    try:
        # List existing buckets
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        if "generated-media" not in bucket_names:
            # Create the bucket with public access
            client.storage.create_bucket(
                "generated-media",
                options={
                    "public": True,
                    "file_size_limit": 52428800,  # 50MB limit
                    "allowed_mime_types": [
                        "image/jpeg",
                        "image/png", 
                        "image/gif",
                        "image/webp",
                        "video/mp4",
                        "video/quicktime",
                        "video/x-m4v"
                    ]
                }
            )
            print("✅ Created 'generated-media' storage bucket")
        else:
            print("✅ 'generated-media' bucket already exists")
            
        # Set up storage policies for the bucket
        # Note: These would need to be set via Supabase dashboard or API
        print("⚠️  Remember to configure storage policies in Supabase dashboard:")
        print("   - Allow authenticated users to upload")
        print("   - Allow public read access")
        
    except Exception as e:
        print(f"❌ Error creating storage bucket: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_storage_bucket())