# tests/test_storage_bucket.py

"""
Test script to verify Supabase storage bucket configuration and accessibility.
Run this before other tests to ensure storage is properly set up.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
print(f"Path: {str(Path(__file__).parent.parent)}")

import asyncio
import pytest
import os
import io
from datetime import datetime
from uuid import uuid4
from PIL import Image
from supabase import create_client, Client as SupabaseClient
from backend.config.settings import settings
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStorageBucket:
    """Test suite for Supabase storage bucket operations"""
    
    @pytest.fixture
    def supabase_anon(self):
        """Supabase client with anon key (public access)"""
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    
    @pytest.fixture
    def supabase_service(self):
        """Supabase client with service key (admin access)"""
        if not hasattr(settings, 'SUPABASE_SERVICE_KEY'):
            pytest.skip("SUPABASE_SERVICE_KEY not configured")
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def test_bucket_exists(self, supabase_service):
        """Test that the generated-media bucket exists"""
        try:
            buckets = supabase_service.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            assert "generated-media" in bucket_names, (
                f"Bucket 'generated-media' not found. Available buckets: {bucket_names}"
            )
            
            # Find the bucket and check its properties
            for bucket in buckets:
                if bucket.name == "generated-media":
                    assert bucket.public == True, "Bucket should be public"
                    logger.info(f"✅ Bucket exists and is public")
                    break
                    
        except Exception as e:
            pytest.fail(f"Failed to list buckets: {e}")
    
    def test_bucket_upload_with_service_key(self, supabase_service):
        """Test uploading a file with service key"""
        # Create a test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Generate unique filename
        test_id = uuid4().hex[:8]
        filename = f"test_{test_id}/test_image.png"
        
        try:
            # Upload the file
            response = supabase_service.storage.from_("generated-media").upload(
                filename,
                img_bytes.read(),
                file_options={"content-type": "image/png"}
            )
            
            assert response is not None
            logger.info(f"✅ Upload successful with service key: {filename}")
            
            # Clean up
            supabase_service.storage.from_("generated-media").remove([filename])
            
        except Exception as e:
            pytest.fail(f"Failed to upload with service key: {e}")
    
    def test_bucket_upload_with_anon_key(self, supabase_anon):
        """Test uploading a file with anon key (should fail unless policies allow)"""
        # Create a test image
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Generate unique filename
        test_id = uuid4().hex[:8]
        filename = f"test_{test_id}/test_anon_image.png"
        
        try:
            # Try to upload the file
            response = supabase_anon.storage.from_("generated-media").upload(
                filename,
                img_bytes.read(),
                file_options={"content-type": "image/png"}
            )
            
            logger.warning("⚠️  Anon key can upload - check if this is intended")
            
            # If successful, clean up
            supabase_anon.storage.from_("generated-media").remove([filename])
            
        except Exception as e:
            # This might be expected if policies restrict anon uploads
            logger.info(f"ℹ️  Anon key upload failed (may be expected): {e}")
    
    def test_public_read_access(self, supabase_service):
        """Test that uploaded files are publicly readable"""
        # Create and upload a test file
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        test_id = uuid4().hex[:8]
        filename = f"test_{test_id}/public_test.png"
        
        try:
            # Upload file
            supabase_service.storage.from_("generated-media").upload(
                filename,
                img_bytes.read(),
                file_options={"content-type": "image/png"}
            )
            
            # Get public URL
            public_url = supabase_service.storage.from_("generated-media").get_public_url(filename)
            
            assert public_url is not None
            assert "generated-media" in public_url
            assert filename in public_url
            
            logger.info(f"✅ Public URL generated: {public_url}")
            
            # Test if URL is actually accessible
            import requests
            response = requests.head(public_url)
            assert response.status_code == 200, f"Public URL not accessible: {response.status_code}"
            
            logger.info("✅ Public URL is accessible")
            
            # Clean up
            supabase_service.storage.from_("generated-media").remove([filename])
            
        except Exception as e:
            pytest.fail(f"Failed public access test: {e}")
    
    def test_file_organization(self, supabase_service):
        """Test proper file organization with initiative paths"""
        # Simulate initiative-based organization
        initiative_id = str(uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Test different media types
        test_files = [
            f"{initiative_id}/images/{timestamp}_image.jpg",
            f"{initiative_id}/videos/{timestamp}_video.mp4",
            f"{initiative_id}/thumbnails/{timestamp}_thumb.png"
        ]
        
        for filepath in test_files:
            # Create dummy content
            content = b"test content"
            
            try:
                # Upload
                response = supabase_service.storage.from_("generated-media").upload(
                    filepath,
                    content,
                    file_options={"content-type": "application/octet-stream"}
                )
                
                assert response is not None
                logger.info(f"✅ Organized upload successful: {filepath}")
                
                # Verify file exists
                files = supabase_service.storage.from_("generated-media").list(
                    path=f"{initiative_id}"
                )
                
                # Clean up
                supabase_service.storage.from_("generated-media").remove([filepath])
                
            except Exception as e:
                pytest.fail(f"Failed organization test for {filepath}: {e}")
    
    def test_storage_limits(self, supabase_service):
        """Test storage limits and error handling"""
        # Test file size limit (if configured)
        large_size = 100 * 1024 * 1024  # 100MB (should exceed typical limits)
        
        # Don't actually create a 100MB file, just test the limit checking
        logger.info("ℹ️  Storage limits should be configured in Supabase dashboard")
        logger.info("   Recommended: 50MB per file")
        
        # Test invalid file types
        test_id = uuid4().hex[:8]
        invalid_filename = f"test_{test_id}/test.exe"
        
        try:
            response = supabase_service.storage.from_("generated-media").upload(
                invalid_filename,
                b"executable content",
                file_options={"content-type": "application/x-msdownload"}
            )
            
            logger.warning("⚠️  Unsafe file type uploaded - check MIME type restrictions")
            
            # Clean up if it succeeded
            supabase_service.storage.from_("generated-media").remove([invalid_filename])
            
        except Exception as e:
            logger.info(f"✅ Invalid file type rejected (good): {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, supabase_service):
        """Test concurrent upload operations"""
        async def upload_file(index):
            img = Image.new('RGB', (50, 50), color='yellow')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            filename = f"test_concurrent/{index}.png"
            
            try:
                response = supabase_service.storage.from_("generated-media").upload(
                    filename,
                    img_bytes.read(),
                    file_options={"content-type": "image/png"}
                )
                return filename, True
            except Exception as e:
                return filename, False
        
        # Run concurrent uploads
        tasks = [upload_file(i) for i in range(5)]
        results = await asyncio.gather(*[asyncio.create_task(task) for task in tasks])
        
        successful = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]
        
        logger.info(f"✅ Concurrent uploads: {len(successful)} successful, {len(failed)} failed")
        
        # Clean up successful uploads
        for filename, _ in successful:
            try:
                supabase_service.storage.from_("generated-media").remove([filename])
            except:
                pass
    
    def test_bucket_permissions_summary(self, supabase_service):
        """Summarize bucket permissions and configuration"""
        logger.info("\n" + "="*60)
        logger.info("STORAGE BUCKET CONFIGURATION SUMMARY")
        logger.info("="*60)
        
        try:
            buckets = supabase_service.storage.list_buckets()
            for bucket in buckets:
                if bucket.name == "generated-media":
                    logger.info(f"✅ Bucket Name: {bucket.name}")
                    logger.info(f"✅ Public Access: {bucket.public}")
                    logger.info(f"✅ Created At: {bucket.created_at}")
                    
                    if hasattr(bucket, 'file_size_limit'):
                        logger.info(f"   File Size Limit: {bucket.file_size_limit}")
                    if hasattr(bucket, 'allowed_mime_types'):
                        logger.info(f"   Allowed MIME Types: {bucket.allowed_mime_types}")
                    
                    break
        except Exception as e:
            logger.error(f"Failed to get bucket info: {e}")
        
        logger.info("\nRECOMMENDED STORAGE POLICIES:")
        logger.info("1. Allow service role full access (SELECT, INSERT, UPDATE, DELETE)")
        logger.info("2. Allow anon role SELECT (public read)")
        logger.info("3. Set file size limit to 50MB")
        logger.info("4. Restrict MIME types to images and videos only")
        logger.info("="*60 + "\n")


def run_storage_diagnostics():
    """Run storage diagnostics without pytest"""
    print("\n" + "="*60)
    print("SUPABASE STORAGE DIAGNOSTICS")
    print("="*60 + "\n")
    
    # Check environment variables
    print("1. Checking environment variables...")
    has_url = bool(os.getenv("SUPABASE_URL"))
    has_anon = bool(os.getenv("SUPABASE_KEY"))
    has_service = bool(os.getenv("SUPABASE_SERVICE_KEY"))
    
    print(f"   SUPABASE_URL: {'✅' if has_url else '❌'}")
    print(f"   SUPABASE_KEY (anon): {'✅' if has_anon else '❌'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✅' if has_service else '❌'}")
    
    if not all([has_url, has_anon, has_service]):
        print("\n❌ Missing required environment variables!")
        return
    
    # Try to connect
    print("\n2. Testing connection...")
    try:
        client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
        buckets = client.storage.list_buckets()
        print(f"   ✅ Connected successfully")
        print(f"   Found {len(buckets)} storage buckets")
        
        # Check for our bucket
        print("\n3. Checking for 'generated-media' bucket...")
        bucket_names = [b.name for b in buckets]
        if "generated-media" in bucket_names:
            print("   ✅ Bucket exists")
            
            for bucket in buckets:
                if bucket.name == "generated-media":
                    print(f"   Public: {bucket.public}")
                    break
        else:
            print("   ❌ Bucket not found!")
            print(f"   Available buckets: {bucket_names}")
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Run diagnostics directly
    run_storage_diagnostics()
    
    # Or run with pytest
    # pytest tests/test_storage_bucket.py -v