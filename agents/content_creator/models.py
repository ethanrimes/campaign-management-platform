# agents/content_creator/models.py

"""
Content Creator agent models that use centralized database models for persistence.
Agent-specific structures for content generation with database model integration.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

# Import centralized database models
from backend.db.models.post import PostsInsert
from backend.db.models.media_file import MediaFilesInsert
from backend.db.models.serialization import serialize_dict, prepare_for_db


class PostType(str, Enum):
    """Types of social media posts"""
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    LINK = "link"
    TEXT = "text"


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
    """Media specifications for agent use"""
    url: str = Field(description="Media URL or generation prompt")
    format: MediaFormat = Field(description="Media format")
    width: Optional[int] = Field(None, ge=1, description="Width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=1, description="Duration for videos")
    file_size_bytes: Optional[int] = Field(None, ge=1, description="File size")
    prompt_used: Optional[str] = Field(None, description="AI generation prompt")
    
    @validator('duration_seconds')
    def validate_video_duration(cls, v, values):
        if 'format' in values and values['format'] in [MediaFormat.MP4, MediaFormat.MOV]:
            if v is None:
                raise ValueError("Video must have duration")
            if v > 90:  # Instagram reel limit
                raise ValueError("Video duration exceeds platform limits")
        return v
    
    def to_db_insert(self, initiative_id: UUID, execution_id: Optional[UUID] = None) -> MediaFilesInsert:
        """Convert to database media file insert"""
        dimensions = None
        if self.width and self.height:
            dimensions = {'width': self.width, 'height': self.height}
        
        file_type = 'video' if self.format in [MediaFormat.MP4, MediaFormat.MOV] else 'image'
        
        return MediaFilesInsert(
            initiative_id=initiative_id,
            file_type=file_type,
            supabase_path=f"generated-media/{initiative_id}/{file_type}s/",
            public_url=self.url,
            dimensions=dimensions,
            duration_seconds=self.duration_seconds,
            file_size_bytes=self.file_size_bytes,
            prompt_used=self.prompt_used,
            execution_id=execution_id,
            execution_step='Content Creation'
        )


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
    """Post content structure for agent use"""
    caption: str = Field(description="Post caption text")
    hashtags: List[str] = Field(default_factory=list, max_items=30)
    mentions: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    emojis_used: List[str] = Field(default_factory=list)
    
    @validator('caption')
    def validate_caption_length(cls, v):
        if len(v) > 2200:  # Instagram limit
            raise ValueError("Caption exceeds Instagram limit (2200 characters)")
        return v
    
    @validator('hashtags')
    def validate_hashtags(cls, v):
        cleaned = []
        for tag in v:
            if not tag.startswith('#'):
                tag = f"#{tag}"
            if len(tag) > 100:
                raise ValueError(f"Hashtag too long: {tag}")
            cleaned.append(tag)
        return cleaned


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
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    agent_id: str = Field(description="Agent ID that generated content")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Post(BaseModel):
    """Individual post structure for agent use"""
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    post_type: PostType = Field(description="Type of post")
    content: PostContent = Field(description="Post content")
    media: List[MediaSpec] = Field(default_factory=list)
    call_to_action: Optional[CallToAction] = Field(None)
    schedule: PostSchedule = Field(description="Scheduling information")
    status: PostStatus = Field(default=PostStatus.DRAFT)
    platform_ids: Dict[str, str] = Field(default_factory=dict)
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
    
    def to_db_insert(
        self, 
        ad_set_id: UUID, 
        initiative_id: UUID,
        execution_id: Optional[UUID] = None
    ) -> PostsInsert:
        """Convert to database post insert"""
        # Extract media URLs
        media_urls = [m.url for m in self.media]
        
        # Build media metadata
        media_metadata = {
            'specs': [serialize_dict(m.dict()) for m in self.media],
            'count': len(self.media)
        }
        
        # Build generation metadata
        gen_metadata = serialize_dict(self.generation_metadata.dict())
        
        return PostsInsert(
            id=UUID(self.post_id) if isinstance(self.post_id, str) else self.post_id,
            ad_set_id=ad_set_id,
            initiative_id=initiative_id,
            post_type=self.post_type.value,
            text_content=self.content.caption,
            hashtags=self.content.hashtags,
            links=self.content.links,
            media_urls=media_urls,
            media_metadata=media_metadata,
            scheduled_time=self.schedule.scheduled_time,
            status=self.status.value,
            is_published=self.status == PostStatus.PUBLISHED,
            generation_metadata=gen_metadata,
            facebook_post_id=self.platform_ids.get('facebook'),
            instagram_post_id=self.platform_ids.get('instagram'),
            execution_id=execution_id,
            execution_step='Content Creation'
        )


class ContentBatch(BaseModel):
    """Batch of generated content for agent use"""
    batch_id: str = Field(default_factory=lambda: str(uuid4()))
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
    
    async def save_to_db(
        self,
        db_client,
        initiative_id: UUID,
        execution_id: Optional[UUID] = None
    ):
        """Save batch of posts to database"""
        saved_posts = []
        
        for post in self.posts:
            # Save post
            post_insert = post.to_db_insert(
                ad_set_id=UUID(self.ad_set_id),
                initiative_id=initiative_id,
                execution_id=execution_id
            )
            saved_post = await db_client.insert("posts", post_insert.to_db_dict())
            saved_posts.append(saved_post)
            
            # Save media files
            for media in post.media:
                media_insert = media.to_db_insert(
                    initiative_id=initiative_id,
                    execution_id=execution_id
                )
                await db_client.insert("media_files", media_insert.to_db_dict())
        
        return saved_posts


class ContentStrategy(BaseModel):
    """Content generation strategy"""
    content_pillars: List[str] = Field(min_items=1, max_items=5)
    posting_schedule: Dict[str, List[str]] = Field(description="Optimal posting times by day")
    hashtag_strategy: str = Field(description="Hashtag strategy")
    engagement_tactics: List[str] = Field(description="Engagement tactics to use")
    visual_guidelines: str = Field(description="Visual content guidelines")


class ContentCreatorOutput(BaseModel):
    """Main content creator output structure for agent use"""
    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    ad_set_id: str = Field(description="Associated ad set ID")
    campaign_id: str = Field(description="Associated campaign ID")
    posts: List[Post] = Field(min_items=1, description="Generated posts")
    content_strategy: ContentStrategy = Field(description="Content strategy used")
    total_posts: int = Field(ge=1, description="Total posts created")
    estimated_reach: Optional[int] = Field(None)
    estimated_engagement: Optional[float] = Field(None)
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization"""
        return serialize_dict(self.dict())


# Export models for agent use
__all__ = [
    'PostType',
    'PostStatus',
    'MediaFormat',
    'MediaSpec',
    'CallToAction',
    'PostContent',
    'PostSchedule',
    'GenerationMetadata',
    'Post',
    'ContentBatch',
    'ContentStrategy',
    'ContentCreatorOutput'
]