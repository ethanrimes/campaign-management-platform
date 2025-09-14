# agents/content_creator/tools/models.py

"""
Pydantic models for social media posting tools.
Defines input/output schemas for Instagram and Facebook posting operations.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from uuid import UUID
from enum import Enum


class MediaType(str, Enum):
    """Supported media types for social posts"""
    IMAGE = "image"
    VIDEO = "video"
    REEL = "reel"
    CAROUSEL = "carousel"
    TEXT = "text"
    LINK = "link"


class PostStatus(str, Enum):
    """Post publication status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class SocialMediaPostInput(BaseModel):
    """Base input model for all social media posts"""
    initiative_id: UUID = Field(
        ...,
        description="UUID of the initiative to fetch tokens and configuration"
    )
    caption: str = Field(
        ...,
        min_length=1,
        max_length=2200,
        description="Post caption/text content (Instagram max: 2200 chars)"
    )
    tags: List[str] = Field(
        default_factory=list,
        max_length=30,
        description="Hashtags or mentions (without # or @ prefix)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (location, audience targeting, etc.)"
    )
    schedule_time: Optional[datetime] = Field(
        None,
        description="Optional scheduled publication time (UTC)"
    )
    
    @field_validator('tags')
    @classmethod
    def clean_tags(cls, v):
        """Remove # or @ prefixes and clean tags"""
        cleaned = []
        for tag in v:
            tag = tag.strip()
            if tag.startswith('#') or tag.startswith('@'):
                tag = tag[1:]
            if tag:  # Skip empty tags
                cleaned.append(tag)
        return cleaned
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "initiative_id": "bf2d9675-b236-4a86-8514-78b0b6d75a53",
                "caption": "Check out our latest updates! 🎉",
                "tags": ["tech", "innovation", "startup"],
                "metadata": {"location": "San Francisco, CA"}
            }
        }
    )


class InstagramImageInput(SocialMediaPostInput):
    """Input model for Instagram image posts"""
    image_prompts: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Prompts for Gemini Imagen 3 to generate images (1-10 for carousel)"
    )
    is_carousel: bool = Field(
        default=False,
        description="Whether to create a carousel post (multiple images)"
    )
    
    @field_validator('image_prompts')
    @classmethod
    def validate_carousel_images(cls, v, info):
        """Ensure carousel posts have 2-10 images"""
        is_carousel = info.data.get('is_carousel', False)
        if is_carousel and len(v) < 2:
            raise ValueError("Carousel posts require at least 2 images")
        return v


class InstagramReelInput(SocialMediaPostInput):
    """Input model for Instagram Reel posts"""
    video_prompt: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Prompt for Gemini Veo 3 to generate video content"
    )
    duration_seconds: int = Field(
        default=15,
        ge=3,
        le=90,
        description="Video duration in seconds (3-90 for Reels)"
    )
    cover_image_prompt: Optional[str] = Field(
        None,
        description="Optional prompt for cover image generation"
    )


class FacebookTextLinkInput(SocialMediaPostInput):
    """Input model for Facebook text + link posts"""
    link_url: str = Field(
        ...,
        pattern=r'^https?://',
        description="URL to share with the post"
    )
    link_preview_title: Optional[str] = Field(
        None,
        max_length=100,
        description="Custom title for link preview"
    )
    link_preview_description: Optional[str] = Field(
        None,
        max_length=200,
        description="Custom description for link preview"
    )


class FacebookImageInput(SocialMediaPostInput):
    """Input model for Facebook image posts"""
    image_prompts: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Prompts for image generation (1 for single, 2-10 for album)"
    )
    is_album: bool = Field(
        default=False,
        description="Whether to create an album post (multiple images)"
    )


class FacebookVideoInput(SocialMediaPostInput):
    """Input model for Facebook video posts"""
    video_prompt: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Prompt for video generation"
    )
    duration_seconds: int = Field(
        default=30,
        ge=3,
        le=240,
        description="Video duration in seconds (3-240 for Facebook)"
    )
    video_title: Optional[str] = Field(
        None,
        max_length=100,
        description="Video title for Facebook"
    )


class MediaFile(BaseModel):
    """Represents a generated media file"""
    file_type: MediaType
    supabase_path: str
    public_url: str
    prompt_used: str
    dimensions: Optional[Dict[str, int]] = None  # width, height
    duration_seconds: Optional[int] = None  # For videos
    file_size_bytes: Optional[int] = None


class PostResponse(BaseModel):
    """Standard response for all social media posts"""
    success: bool = Field(
        description="Whether the post was successfully published"
    )
    post_id: Optional[str] = Field(
        None,
        description="Platform-specific post ID"
    )
    post_url: Optional[str] = Field(
        None,
        description="Public URL to view the post"
    )
    status: PostStatus = Field(
        description="Current status of the post"
    )
    media_files: List[MediaFile] = Field(
        default_factory=list,
        description="Generated and uploaded media files"
    )
    platform: Literal["instagram", "facebook"] = Field(
        description="Social media platform"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if posting failed"
    )
    container_id: Optional[str] = Field(
        None,
        description="Instagram container ID (for multi-step publishing)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "post_id": "18155706172387258",
                "post_url": "https://www.instagram.com/p/ABC123/",
                "status": "published",
                "media_files": [{
                    "file_type": "image",
                    "supabase_path": "generated-media/bf2d.../images/img_001.jpg",
                    "public_url": "https://storage.supabase.co/...",
                    "prompt_used": "A beautiful sunset over mountains"
                }],
                "platform": "instagram"
            }
        }
    )


class BatchPostRequest(BaseModel):
    """Request to post to multiple platforms simultaneously"""
    initiative_id: UUID
    caption: str
    tags: List[str] = Field(default_factory=list)
    platforms: List[Literal["instagram", "facebook"]] = Field(
        ...,
        min_length=1,
        description="Platforms to post to"
    )
    media_prompts: List[str] = Field(
        default_factory=list,
        description="Media generation prompts"
    )
    media_type: MediaType = Field(
        MediaType.IMAGE,
        description="Type of media to generate and post"
    )


class BatchPostResponse(BaseModel):
    """Response for batch posting operations"""
    results: Dict[str, PostResponse] = Field(
        description="Results per platform"
    )
    total_success: int = Field(
        description="Number of successful posts"
    )
    total_failed: int = Field(
        description="Number of failed posts"
    )