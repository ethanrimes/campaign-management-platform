# test_existing_video_post.py

"""
Test posting an existing video URL directly to Instagram and Facebook.
This bypasses generation to isolate posting issues.
"""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.token_manager import TokenManager
from supabase import create_client
import aiohttp

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_INITIATIVE_ID = UUID("bf2d9675-b236-4a86-8514-78b0b6d75a53")
EXISTING_VIDEO_URL = "https://d2p7pge43lyniu.cloudfront.net/output/9f84e4e8-733d-41b7-aeae-c44ad983965c-u1_05fb4e0f-58ba-4444-8209-4c3ed2554a97.mp4"

# Meta API configuration
META_API_VERSION = "v23.0"
INSTAGRAM_API_BASE = f"https://graph.instagram.com/{META_API_VERSION}"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


async def test_video_download():
    """Test if we can download the video"""
    logger.info("=" * 60)
    logger.info("Testing video download")
    logger.info("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        logger.info(f"Downloading from: {EXISTING_VIDEO_URL}")
        
        try:
            async with session.get(EXISTING_VIDEO_URL) as response:
                logger.info(f"Response status: {response.status}")
                logger.info(f"Content-Type: {response.headers.get('Content-Type')}")
                logger.info(f"Content-Length: {response.headers.get('Content-Length')}")
                
                if response.status == 200:
                    content = await response.read()
                    logger.info(f"✅ Downloaded {len(content):,} bytes")
                    return content
                else:
                    logger.error(f"❌ Download failed: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return None


async def upload_to_supabase(video_bytes):
    """Upload video to Supabase"""
    logger.info("=" * 60)
    logger.info("Uploading to Supabase")
    logger.info("=" * 60)
    
    from backend.config.settings import settings
    from datetime import datetime, timezone
    from uuid import uuid4
    
    try:
        # Initialize Supabase client
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Generate unique filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_id = uuid4().hex[:8]
        filename = f"test_video_{timestamp}_{file_id}.mp4"
        storage_path = f"{TEST_INITIATIVE_ID}/videos/{filename}"
        
        logger.info(f"Uploading {len(video_bytes):,} bytes to: {storage_path}")
        
        # Upload to Supabase
        supabase.storage.from_("generated-media").upload(
            storage_path,
            video_bytes,
            file_options={"content-type": "video/mp4"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("generated-media").get_public_url(storage_path)
        logger.info(f"✅ Uploaded to: {public_url}")
        
        return public_url
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return None


async def test_instagram_reel_post(video_url):
    """Test posting video as Instagram Reel"""
    logger.info("=" * 60)
    logger.info("Testing Instagram Reel Post")
    logger.info("=" * 60)
    
    try:
        # Get Instagram tokens
        token_manager = TokenManager(str(TEST_INITIATIVE_ID))
        tokens = await token_manager.get_instagram_tokens()
        
        ig_user_id = tokens["business_id"]
        access_token = tokens["access_token"]
        
        logger.info(f"Instagram Business ID: {ig_user_id}")
        logger.info(f"Access token: {access_token[:10]}...")
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Create media container for Reel
            logger.info("Creating Reel container...")
            url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
            
            params = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": "Test Reel with existing video 🎬 #test #video #reel",
                "access_token": access_token
            }
            
            async with session.post(url, json=params) as response:
                result = await response.json()
                logger.debug(f"Create container response: {result}")
                
                if "id" in result:
                    container_id = result["id"]
                    logger.info(f"✅ Container created: {container_id}")
                else:
                    logger.error(f"❌ Container creation failed: {result}")
                    return False
            
            # Step 2: Check container status
            logger.info("Checking container status...")
            for i in range(30):  # Check for up to 60 seconds
                await asyncio.sleep(2)
                
                status_url = f"{INSTAGRAM_API_BASE}/{container_id}"
                params = {
                    "fields": "status_code",
                    "access_token": access_token
                }
                
                async with session.get(status_url, params=params) as response:
                    result = await response.json()
                    status = result.get("status_code", "UNKNOWN")
                    logger.debug(f"Attempt {i+1}: Status = {status}")
                    
                    if status == "FINISHED":
                        logger.info("✅ Container ready")
                        break
                    elif status == "ERROR":
                        logger.error(f"❌ Container processing failed: {result}")
                        return False
            
            # Step 3: Publish the Reel
            logger.info("Publishing Reel...")
            publish_url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media_publish"
            params = {
                "creation_id": container_id,
                "access_token": access_token
            }
            
            async with session.post(publish_url, json=params) as response:
                result = await response.json()
                logger.debug(f"Publish response: {result}")
                
                if "id" in result:
                    post_id = result["id"]
                    logger.info(f"✅ Reel published: {post_id}")
                    logger.info(f"View at: https://www.instagram.com/reel/{post_id}/")
                    return True
                else:
                    logger.error(f"❌ Publishing failed: {result}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Instagram Reel post failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_facebook_video_post(video_url):
    """Test posting video to Facebook"""
    logger.info("=" * 60)
    logger.info("Testing Facebook Video Post")
    logger.info("=" * 60)
    
    try:
        # Get Facebook tokens
        token_manager = TokenManager(str(TEST_INITIATIVE_ID))
        tokens = await token_manager.get_facebook_tokens()
        
        page_id = tokens["page_id"]
        access_token = tokens["page_access_token"]
        
        logger.info(f"Facebook Page ID: {page_id}")
        logger.info(f"Access token: {access_token[:10]}...")
        
        async with aiohttp.ClientSession() as session:
            # Post video to Facebook
            logger.info("Posting video to Facebook...")
            url = f"{META_API_BASE}/{page_id}/videos"
            
            params = {
                "file_url": video_url,
                "description": "Test video post with existing video 🎥 #test #video",
                "title": "Test Video Upload",
                "access_token": access_token
            }
            
            async with session.post(url, json=params) as response:
                result = await response.json()
                logger.debug(f"Post response: {result}")
                
                if "id" in result:
                    video_id = result["id"]
                    logger.info(f"✅ Video posted: {video_id}")
                    logger.info(f"View at: https://www.facebook.com/{page_id}/videos/{video_id}")
                    return True
                else:
                    logger.error(f"❌ Video post failed: {result}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Facebook video post failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    logger.info("Starting video posting tests")
    logger.info(f"Initiative ID: {TEST_INITIATIVE_ID}")
    logger.info(f"Video URL: {EXISTING_VIDEO_URL}")
    
    # Test 1: Download video
    video_bytes = await test_video_download()
    if not video_bytes:
        logger.error("Failed to download video, aborting tests")
        return
    
    # Test 2: Upload to Supabase
    supabase_url = await upload_to_supabase(video_bytes)
    if not supabase_url:
        logger.error("Failed to upload to Supabase, aborting tests")
        return
    
    logger.info(f"Using Supabase URL for posting: {supabase_url}")
    
    # Test 3: Post to Instagram as Reel
    instagram_success = await test_instagram_reel_post(supabase_url)
    
    # Test 4: Post to Facebook
    facebook_success = await test_facebook_video_post(supabase_url)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Video Download: ✅")
    logger.info(f"Supabase Upload: ✅")
    logger.info(f"Instagram Reel: {'✅' if instagram_success else '❌'}")
    logger.info(f"Facebook Video: {'✅' if facebook_success else '❌'}")
    

if __name__ == "__main__":
    asyncio.run(main())