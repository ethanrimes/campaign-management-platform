# tests/test_content_generation.py

"""
Tests for social media content generation and posting tools.
Uses test initiative with pre-configured tokens.

Usage:
    pytest tests/test_content_generation.py -v                          # Run all tests
    pytest tests/test_content_generation.py::test_instagram_image_post  # Run specific test
    python tests/test_content_generation.py --test image               # Run image tests only
    python tests/test_content_generation.py --test video               # Run video tests only
    python tests/test_content_generation.py --test existing-video      # Test with existing video
"""

import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
import os
import argparse
from uuid import UUID
from datetime import datetime
from pathlib import Path
import logging
import sys
from typing import List

from agents.content_creator.tools.social_media_posting import (
    instagram_image_post_tool,
    instagram_reel_post_tool,
    facebook_text_link_post_tool,
    facebook_image_post_tool,
    facebook_video_post_tool
)
from agents.content_creator.tools.models import PostStatus
from backend.services.media_generation import (
    ImageGenerationService,
    VideoGenerationService
)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test initiative ID (must have valid tokens in database)
TEST_INITIATIVE_ID = UUID("bf2d9675-b236-4a86-8514-78b0b6d75a53")

# Test configuration
TEST_CONFIG = {
    "generation_timeout": 180,  # Increased timeout for video generation
    "posting_timeout": 60,
    "retry_attempts": 3,
    "use_placeholders": os.getenv("USE_PLACEHOLDER_MEDIA", "false").lower() == "true"
}


@pytest.fixture
def initiative_id():
    """Provide test initiative ID"""
    return str(TEST_INITIATIVE_ID)


@pytest.fixture
def media_urls_list():
    """Fixture to store generated media URLs for cleanup"""
    urls = []
    yield urls
    # Cleanup logic if needed
    for url in urls:
        logger.info(f"Generated media URL: {url}")


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"])
async def test_image_generation_service(initiative_id):
    """Test image generation service with Wavespeed"""
    service = ImageGenerationService()
    
    prompts = [
        "A serene landscape with mountains and a lake at sunset, photorealistic, 4k quality",
        "Modern minimalist office space with natural lighting, architectural photography"
    ]
    
    logger.info("Starting image generation test...")
    logger.debug(f"Using initiative_id: {initiative_id}")
    logger.debug(f"Prompts: {prompts}")
    
    urls = await service.generate_images(
        prompts=prompts,
        initiative_id=UUID(initiative_id),
        num_per_prompt=1
    )
    
    logger.info(f"Generated {len(urls)} images")
    assert len(urls) >= 1, "Should generate at least one image"
    for url in urls:
        assert url.startswith("http"), f"Invalid URL: {url}"
        assert "generated-media" in url, f"URL not from Supabase: {url}"
        logger.info(f"✅ Generated image: {url}")


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] * 2)
async def test_video_generation_service(initiative_id):
    """Test video generation service with Wavespeed"""
    service = VideoGenerationService()
    
    prompt = "Time-lapse of a city skyline transitioning from day to night, cinematic"
    
    logger.info("Starting video generation test...")
    logger.debug(f"Using initiative_id: {initiative_id}")
    logger.debug(f"Prompt: {prompt}")
    
    url = await service.generate_video(
        prompt=prompt,
        initiative_id=UUID(initiative_id),
        duration_sec=5
    )
    
    logger.info(f"Generated video URL: {url}")
    assert url.startswith("http"), f"Invalid URL: {url}"
    assert "generated-media" in url, f"URL not from Supabase: {url}"
    logger.info(f"✅ Generated video: {url}")


@pytest.mark.asyncio
async def test_with_existing_video(initiative_id):
    """Test posting with a known working video URL"""
    logger.info("Testing with existing Wavespeed video...")
    
    # Use the known working video URL
    existing_video_url = "https://d2p7pge43lyniu.cloudfront.net/output/9f84e4e8-733d-41b7-aeae-c44ad983965c-u1_05fb4e0f-58ba-4444-8209-4c3ed2554a97.mp4"
    
    # Test direct video download
    import aiohttp
    async with aiohttp.ClientSession() as session:
        logger.debug(f"Attempting to download video from: {existing_video_url}")
        async with session.get(existing_video_url) as response:
            logger.debug(f"Response status: {response.status}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status == 200:
                video_bytes = await response.read()
                logger.info(f"✅ Successfully downloaded video: {len(video_bytes)} bytes")
                
                # Now try to upload to Supabase and post
                from backend.services.media_generation import MediaGenerationService
                service = MediaGenerationService()
                
                public_url = await service._upload_to_supabase(
                    file_bytes=video_bytes,
                    initiative_id=UUID(initiative_id),
                    media_type="videos",
                    file_extension="mp4",
                    content_type="video/mp4",
                    metadata={
                        "test": "existing_video",
                        "original_url": existing_video_url
                    }
                )
                
                logger.info(f"✅ Uploaded to Supabase: {public_url}")
                
                # Test posting to Instagram as Reel
                logger.info("Testing Instagram Reel post with existing video...")
                # Note: This would need modification to accept pre-generated video URL
                # For now, just verify the download and upload worked
                
            else:
                logger.error(f"Failed to download video: HTTP {response.status}")
                assert False, f"Video download failed with status {response.status}"


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] + TEST_CONFIG["posting_timeout"])
async def test_instagram_image_post(initiative_id, media_urls_list):
    """Test posting a single image to Instagram with generation"""
    logger.info("Starting Instagram image post test...")
    
    result = await instagram_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Testing automated image post with Wavespeed AI! 🚀",
        tags=["aiart", "automation", "wavespeed"],
        image_prompts=["A futuristic robot artist painting on a holographic canvas, digital art style"],
        is_carousel=False,
        metadata={"test_run": True, "timestamp": datetime.utcnow().isoformat()}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "instagram"
    assert result.post_id is not None
    assert result.post_url is not None
    assert len(result.media_files) == 1
    
    logger.info(f"✅ Successfully posted to Instagram: {result.post_url}")
    media_urls_list.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] * 3 + TEST_CONFIG["posting_timeout"])
async def test_instagram_carousel_post(initiative_id, media_urls_list):
    """Test posting a carousel to Instagram with multiple generated images"""
    logger.info("Starting Instagram carousel post test...")
    
    result = await instagram_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Amazing AI-generated carousel! Swipe to see more 🎨",
        tags=["carousel", "aiart", "creativity"],
        image_prompts=[
            "Abstract geometric art with vibrant neon colors",
            "Minimalist zen garden with perfect symmetry",
            "Futuristic cityscape with flying vehicles"
        ],
        is_carousel=True,
        metadata={"test_type": "carousel"}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert len(result.media_files) == 3
    
    logger.info(f"✅ Successfully posted carousel to Instagram: {result.post_url}")
    media_urls_list.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] * 2 + TEST_CONFIG["posting_timeout"])
async def test_instagram_reel_post(initiative_id, media_urls_list):
    """Test posting a Reel to Instagram with generated video"""
    logger.info("Starting Instagram Reel post test...")
    
    result = await instagram_reel_post_tool._arun(
        initiative_id=initiative_id,
        caption="AI-generated Reel with Wavespeed! 🎬",
        tags=["reels", "aivideo", "wavespeed"],
        video_prompt="Dynamic animation of colorful abstract shapes morphing and flowing",
        duration_seconds=5,
        cover_image_prompt="Vibrant abstract art thumbnail with bold colors",
        metadata={"format": "reel", "ai_generated": True}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert any(mf.file_type == "reel" for mf in result.media_files)
    
    logger.info(f"✅ Successfully posted Reel to Instagram: {result.post_url}")
    media_urls_list.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["posting_timeout"])
async def test_facebook_text_link_post(initiative_id):
    """Test posting text with link to Facebook"""
    logger.info("Starting Facebook text+link post test...")
    
    result = await facebook_text_link_post_tool._arun(
        initiative_id=initiative_id,
        caption="Check out the latest in AI-powered content creation!",
        tags=["AI", "automation", "technology"],
        link_url="https://example.com/ai-content-creation",
        metadata={"content_type": "article"}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "facebook"
    
    logger.info(f"✅ Successfully posted to Facebook: {result.post_id}")


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] + TEST_CONFIG["posting_timeout"])
async def test_facebook_image_post(initiative_id, media_urls_list):
    """Test posting an image to Facebook with generation"""
    logger.info("Starting Facebook image post test...")
    
    result = await facebook_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Beautiful AI art created with Wavespeed! 🎨",
        tags=["aiart", "digitalart", "wavespeed"],
        image_prompts=["Impressionist painting of a peaceful garden with blooming flowers"],
        is_album=False,
        metadata={"art_style": "impressionist"}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert len(result.media_files) == 1
    
    logger.info(f"✅ Successfully posted image to Facebook: {result.post_id}")
    media_urls_list.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_CONFIG["generation_timeout"] * 2 + TEST_CONFIG["posting_timeout"])
async def test_facebook_video_post(initiative_id, media_urls_list):
    """Test posting a video to Facebook with generation"""
    logger.info("Starting Facebook video post test...")
    
    result = await facebook_video_post_tool._arun(
        initiative_id=initiative_id,
        caption="Incredible AI-generated video with Wavespeed! 🎥",
        tags=["video", "aigenerated", "innovation"],
        video_prompt="Smooth animation of liquid metal transforming into geometric shapes",
        duration_seconds=5,
        video_title="AI Video Generation Demo",
        metadata={"video_type": "animation"}
    )
    
    logger.debug(f"Post result: {result}")
    assert result.success is True, f"Post should succeed: {result.error_message}"
    assert result.status == PostStatus.PUBLISHED
    assert any(mf.file_type == "video" for mf in result.media_files)
    
    logger.info(f"✅ Successfully posted video to Facebook: {result.post_id}")
    media_urls_list.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_error_handling_invalid_initiative():
    """Test error handling with invalid initiative ID"""
    invalid_id = "00000000-0000-0000-0000-000000000000"
    
    logger.info("Testing error handling with invalid initiative...")
    result = await instagram_image_post_tool._arun(
        initiative_id=invalid_id,
        caption="This should fail",
        tags=["test"],
        image_prompts=["Test prompt"],
        is_carousel=False
    )
    
    assert result.success is False
    assert result.status == PostStatus.FAILED
    assert result.error_message is not None
    logger.info(f"✅ Error handled correctly: {result.error_message}")


# CLI support for running specific tests
def main():
    parser = argparse.ArgumentParser(description='Run social media posting tests')
    parser.add_argument('--test', choices=['all', 'image', 'video', 'instagram', 'facebook', 'existing-video'],
                        default='all', help='Which tests to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine which tests to run
    test_functions = []
    
    if args.test == 'all':
        test_functions = [
            test_image_generation_service,
            test_video_generation_service,
            test_instagram_image_post,
            test_instagram_carousel_post,
            test_instagram_reel_post,
            test_facebook_text_link_post,
            test_facebook_image_post,
            test_facebook_video_post,
            test_error_handling_invalid_initiative
        ]
    elif args.test == 'image':
        test_functions = [
            test_image_generation_service,
            test_instagram_image_post,
            test_instagram_carousel_post,
            test_facebook_image_post
        ]
    elif args.test == 'video':
        test_functions = [
            test_video_generation_service,
            test_instagram_reel_post,
            test_facebook_video_post
        ]
    elif args.test == 'instagram':
        test_functions = [
            test_instagram_image_post,
            test_instagram_carousel_post,
            test_instagram_reel_post
        ]
    elif args.test == 'facebook':
        test_functions = [
            test_facebook_text_link_post,
            test_facebook_image_post,
            test_facebook_video_post
        ]
    elif args.test == 'existing-video':
        test_functions = [test_with_existing_video]
    
    # Run tests
    async def run_tests():
        initiative_id = str(TEST_INITIATIVE_ID)
        media_urls = []
        
        for test_func in test_functions:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Running: {test_func.__name__}")
                logger.info(f"{'='*60}")
                
                # Check if test needs media_urls_list fixture
                if 'media_urls_list' in test_func.__code__.co_varnames:
                    await test_func(initiative_id, media_urls)
                else:
                    await test_func(initiative_id)
                
                logger.info(f"✅ {test_func.__name__} PASSED")
            except Exception as e:
                logger.error(f"❌ {test_func.__name__} FAILED: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Test run complete. Generated media URLs:")
        for url in media_urls:
            logger.info(f"  - {url}")
    
    # Run async tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    # Check if running with pytest or as script
    if 'pytest' in sys.modules:
        # Running with pytest, don't execute main
        pass
    else:
        # Running as script
        main()