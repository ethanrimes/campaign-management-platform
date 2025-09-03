# agents/content_creator/models.py

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class PostType(str, Enum):
    """Types of social media posts"""
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"


class PostStatus(str, Enum):
    """Post publication status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaFormat(str, Enum):
    """Media format types"""
    JPEG = "jpeg"
    PNG = "png"
    MP4 = "mp4"
    MOV = "mov"
    GIF = "gif"


class MediaSpec(BaseModel):
    """Media specifications"""
    url: str = Field(description="Media URL")
    format: MediaFormat = Field(description="Media format")
    width: Optional[int] = Field(None, ge=1, description="Width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=1, description="Duration for videos")
    file_size_bytes: Optional[int] = Field(None, ge=1, description="File size")
    
    @validator('duration_seconds')
    def validate_video_duration(cls, v, values):
        if 'format' in values and values['format'] in [MediaFormat.MP4, MediaFormat.MOV]:
            if v is None:
                raise ValueError("Video must have duration")
            if v > 60:  # Instagram story/reel limit
                raise ValueError("Video duration exceeds platform limits")
        return v


class CallToAction(BaseModel):
    """Call to action configuration"""
    text: str = Field(description="CTA text")
    action_type: str = Field(default="learn_more", description="CTA type")
    destination_url: Optional[str] = Field(None, description="Link destination")
    
    @validator('text')
    def validate_cta_length(cls, v):
        if len(v) > 30:
            raise ValueError("CTA text too long (max 30 characters)")
        return v


class PostContent(BaseModel):
    """Post content structure"""
    caption: str = Field(description="Post caption text")
    hashtags: List[str] = Field(default_factory=list, max_items=30, description="Hashtags")
    mentions: List[str] = Field(default_factory=list, description="Account mentions")
    links: List[str] = Field(default_factory=list, description="Embedded links")
    emojis_used: List[str] = Field(default_factory=list, description="Emojis in content")
    
    @validator('caption')
    def validate_caption_length(cls, v):
        if len(v) > 2200:  # Instagram limit
            raise ValueError("Caption exceeds Instagram limit (2200 characters)")
        return v
    
    @validator('hashtags')
    def validate_hashtags(cls, v):
        for tag in v:
            if not tag.startswith('#'):
                raise ValueError(f"Invalid hashtag format: {tag}")
            if len(tag) > 100:
                raise ValueError(f"Hashtag too long: {tag}")
        return v


class PostSchedule(BaseModel):
    """Post scheduling information"""
    scheduled_time: datetime = Field(description="Scheduled publication time")
    timezone: str = Field(default="UTC", description="Timezone")
    optimal_time: bool = Field(default=False, description="Is this an optimal posting time")
    
    @validator('scheduled_time')
    def validate_future_time(cls, v):
        if v < datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")
        return v


class GenerationMetadata(BaseModel):
    """Metadata about content generation"""
    model_used: str = Field(description="AI model used")
    prompt_tokens: Optional[int] = Field(None, description="Prompt token count")
    completion_tokens: Optional[int] = Field(None, description="Completion token count")
    generation_time_seconds: Optional[float] = Field(None, description="Generation time")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature setting")
    agent_id: str = Field(description="Agent ID that generated content")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Post(BaseModel):
    """Individual post structure"""
    post_id: str = Field(description="Unique post ID")
    post_type: PostType = Field(description="Type of post")
    content: PostContent = Field(description="Post content")
    media: List[MediaSpec] = Field(default_factory=list, description="Media files")
    call_to_action: Optional[CallToAction] = Field(None, description="CTA configuration")
    schedule: PostSchedule = Field(description="Scheduling information")
    status: PostStatus = Field(default=PostStatus.DRAFT, description="Post status")
    platform_ids: Dict[str, str] = Field(
        default_factory=dict,
        description="Platform-specific post IDs"
    )
    generation_metadata: GenerationMetadata = Field(description="Generation metadata")
    
    @validator('media')
    def validate_media_requirements(cls, v, values):
        if 'post_type' in values:
            post_type = values['post_type']
            if post_type == PostType.IMAGE and len(v) != 1:
                raise ValueError("Image post must have exactly 1 media file")
            elif post_type == PostType.CAROUSEL and (len(v) < 2 or len(v) > 10):
                raise ValueError("Carousel must have 2-10 media files")
            elif post_type == PostType.VIDEO and len(v) != 1:
                raise ValueError("Video post must have exactly 1 media file")
        return v


class ContentBatch(BaseModel):
    """Batch of generated content"""
    batch_id: str = Field(description="Batch ID")
    ad_set_id: str = Field(description="Associated ad set ID")
    posts: List[Post] = Field(min_items=1, description="Generated posts")
    theme: str = Field(description="Content theme")
    target_audience: str = Field(description="Target audience")
    
    @validator('posts')
    def validate_post_variety(cls, v):
        # Ensure variety in post types
        post_types = [post.post_type for post in v]
        if len(set(post_types)) < min(2, len(v)):
            # Warning: low variety, but don't fail
            pass
        return v


class ContentStrategy(BaseModel):
    """Content generation strategy"""
    content_pillars: List[str] = Field(
        min_items=1,
        max_items=5,
        description="Content pillars/themes"
    )
    posting_schedule: Dict[str, List[str]] = Field(
        description="Optimal posting times by day"
    )
    hashtag_strategy: str = Field(description="Hashtag strategy")
    engagement_tactics: List[str] = Field(description="Engagement tactics to use")
    visual_guidelines: str = Field(description="Visual content guidelines")


class ContentCreatorOutput(BaseModel):
    """Main content creator output structure"""
    batch_id: str = Field(description="Content batch ID")
    ad_set_id: str = Field(description="Associated ad set ID")
    campaign_id: str = Field(description="Associated campaign ID")
    posts: List[Post] = Field(min_items=1, description="Generated posts")
    content_strategy: ContentStrategy = Field(description="Content strategy used")
    total_posts: int = Field(ge=1, description="Total posts created")
    estimated_reach: Optional[int] = Field(None, description="Estimated total reach")
    estimated_engagement: Optional[float] = Field(None, description="Estimated engagement rate")
    creation_summary: str = Field(description="Summary of content created")
    
    @validator('total_posts')
    def validate_post_count(cls, v, values):
        if 'posts' in values and v != len(values['posts']):
            raise ValueError("Total posts count doesn't match posts array length")
        return v
    
    @validator('posts')
    def validate_unique_ids(cls, v):
        post_ids = [post.post_id for post in v]
        if len(post_ids) != len(set(post_ids)):
            raise ValueError("Duplicate post IDs found")
        return v