# backend/db/models/post.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4


class Post(BaseModel):
    """Post/Content model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    ad_set_id: str
    
    # Content
    post_type: str  # image, video, carousel, story
    text_content: Optional[str] = None
    hashtags: Optional[List[str]] = None
    links: Optional[List[str]] = None  # Embedded links
    
    # Media
    media_urls: Optional[List[str]] = None  # List of image/video URLs
    media_metadata: Optional[Dict[str, Any]] = None  # Dimensions, duration, etc.
    
    # Schedule
    scheduled_time: Optional[datetime] = None
    published_time: Optional[datetime] = None
    
    # Platform-specific IDs
    facebook_post_id: Optional[str] = None
    instagram_post_id: Optional[str] = None
    
    # Status
    status: str = "draft"  # draft, scheduled, published, failed
    is_published: bool = False
    
    # Performance
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    clicks: int = 0
    comments_count: int = 0
    shares: int = 0
    
    # AI Generation Metadata
    generation_metadata: Optional[Dict[str, Any]] = None  # Model used, prompts, etc.
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
