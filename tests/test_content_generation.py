# tests/test_content_generation.py

"""
Tests for social media content generation and posting tools.
Uses test initiative with pre-configured tokens.
"""

import pytest
import asyncio
import os
from uuid import UUID
from datetime import datetime
from pathlib import Path

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

# Test initiative ID (must have valid tokens in database)
TEST_INITIATIVE_ID = UUID("bf2d9675-b236-4a86-8514-78b0b6d75a53")

# Test configuration
TEST_CONFIG = {
    "timeout": 60,  # seconds
    "retry_attempts": 3,
    "use_placeholders": os.getenv("USE_PLACEHOLDER_MEDIA", "false").lower() == "true"
}


@pytest.fixture
def initiative_id():
    """Provide test initiative ID"""
    return str(TEST_INITIATIVE_ID)


@pytest.fixture
async def cleanup_media():
    """Cleanup generated media after tests"""
    created_files = []
    yield created_files
    
    # Cleanup logic if needed
    for file_path in created_files:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            print(f"Failed to cleanup {file_path}: {e}")


@pytest.mark.asyncio
async def test_image_generation_service(initiative_id):
    """Test image generation service"""
    service = ImageGenerationService()
    
    prompts = [
        "A serene landscape with mountains and a lake at sunset",
        "Modern minimalist office space with natural lighting"
    ]
    
    urls = await service.generate_images(
        prompts=prompts,
        initiative_id=UUID(initiative_id),
        num_per_prompt=1
    )
    
    assert len(urls) == len(prompts)
    for url in urls:
        assert url.startswith("http")
        assert "generated-media" in url


@pytest.mark.asyncio
async def test_video_generation_service(initiative_id):
    """Test video generation service"""
    service = VideoGenerationService()
    
    prompt = "Time-lapse of a city skyline from day to night"
    
    url = await service.generate_video(
        prompt=prompt,
        initiative_id=UUID(initiative_id),
        duration_sec=10
    )
    
    assert url.startswith("http")
    assert "generated-media" in url


@pytest.mark.asyncio
async def test_instagram_image_post(initiative_id, cleanup_media):
    """Test posting a single image to Instagram"""
    result = await instagram_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Testing automated image post from Python! 🚀",
        tags=["pythondev", "automation", "testing"],
        image_prompts=["A futuristic robot writing code on a holographic screen"],
        is_carousel=False,
        metadata={"test_run": True, "timestamp": datetime.utcnow().isoformat()}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "instagram"
    assert result.post_id is not None
    assert result.post_url is not None
    assert len(result.media_files) == 1
    
    # Track media for cleanup
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_instagram_carousel_post(initiative_id, cleanup_media):
    """Test posting a carousel (multiple images) to Instagram"""
    result = await instagram_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Check out this amazing carousel post! 🎨",
        tags=["carousel", "multipost", "creativity"],
        image_prompts=[
            "Abstract art with vibrant colors and geometric shapes",
            "Minimalist design with clean lines and negative space",
            "Nature photography of a waterfall in a forest"
        ],
        is_carousel=True,
        metadata={"test_type": "carousel"}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "instagram"
    assert len(result.media_files) == 3
    
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_instagram_reel_post(initiative_id, cleanup_media):
    """Test posting a Reel to Instagram"""
    result = await instagram_reel_post_tool._arun(
        initiative_id=initiative_id,
        caption="Amazing Reel created with AI! 🎬",
        tags=["reels", "aigenerated", "videoContent"],
        video_prompt="Dynamic montage of technology and innovation scenes",
        duration_seconds=15,
        cover_image_prompt="Futuristic technology thumbnail",
        metadata={"format": "reel", "ai_generated": True}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "instagram"
    assert result.post_id is not None
    assert any(mf.file_type == "reel" for mf in result.media_files)
    
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_facebook_text_link_post(initiative_id):
    """Test posting text with link to Facebook"""
    result = await facebook_text_link_post_tool._arun(
        initiative_id=initiative_id,
        caption="Check out this amazing article about AI and social media!",
        tags=["AI", "socialmedia", "technology"],
        link_url="https://example.com/ai-social-media-article",
        link_preview_title="AI Revolutionizes Social Media",
        link_preview_description="How artificial intelligence is transforming social platforms",
        metadata={"content_type": "article"}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "facebook"
    assert result.post_id is not None


@pytest.mark.asyncio
async def test_facebook_image_post(initiative_id, cleanup_media):
    """Test posting a single image to Facebook"""
    result = await facebook_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Beautiful AI-generated artwork! 🎨",
        tags=["aiart", "digitalart", "creativity"],
        image_prompts=["Impressionist painting of a garden in bloom"],
        is_album=False,
        metadata={"art_style": "impressionist"}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "facebook"
    assert len(result.media_files) == 1
    
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_facebook_album_post(initiative_id, cleanup_media):
    """Test posting an album (multiple images) to Facebook"""
    result = await facebook_image_post_tool._arun(
        initiative_id=initiative_id,
        caption="Photo album showcase! 📸",
        tags=["photoalbum", "collection", "showcase"],
        image_prompts=[
            "Sunset over ocean waves",
            "Mountain landscape with snow peaks",
            "City skyline at night with lights"
        ],
        is_album=True,
        metadata={"album_theme": "landscapes"}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "facebook"
    assert len(result.media_files) == 3
    
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_facebook_video_post(initiative_id, cleanup_media):
    """Test posting a video to Facebook"""
    result = await facebook_video_post_tool._arun(
        initiative_id=initiative_id,
        caption="Incredible AI-generated video content! 🎥",
        tags=["video", "aigenerated", "innovation"],
        video_prompt="Smooth animation of abstract shapes morphing and transitioning",
        duration_seconds=20,
        video_title="AI Video Generation Demo",
        metadata={"video_type": "animation"}
    )
    
    assert result.success is True
    assert result.status == PostStatus.PUBLISHED
    assert result.platform == "facebook"
    assert any(mf.file_type == "video" for mf in result.media_files)
    
    cleanup_media.extend([mf.public_url for mf in result.media_files])


@pytest.mark.asyncio
async def test_error_handling_invalid_initiative():
    """Test error handling with invalid initiative ID"""
    invalid_id = "00000000-0000-0000-0000-000000000000"
    
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


@pytest.mark.asyncio
async def test_caption_length_validation():
    """Test caption length validation"""
    from agents.content_creator.tools.models import InstagramImageInput
    
    # Test too long caption (Instagram max is 2200)
    long_caption = "x" * 2201
    
    with pytest.raises(ValueError):
        InstagramImageInput(
            initiative_id=TEST_INITIATIVE_ID,
            caption=long_caption,
            image_prompts=["test"]
        )


@pytest.mark.asyncio
async def test_hashtag_cleaning():
    """Test hashtag cleaning functionality"""
    from agents.content_creator.tools.models import SocialMediaPostInput
    
    input_data = SocialMediaPostInput(
        initiative_id=TEST_INITIATIVE_ID,
        caption="Test post",
        tags=["#hashtag1", "@mention1", "  clean_tag  ", "#", ""]
    )
    
    # Should clean tags by removing # and @, trimming spaces
    assert input_data.tags == ["hashtag1", "mention1", "clean_tag"]


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])