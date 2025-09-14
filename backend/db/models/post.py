# backend/db/models/post.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any, List
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class PostsBaseSchema(CustomModel):
    """Posts Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    ad_set_id: UUID4
    clicks: Optional[int] = Field(default=None)
    comments_count: Optional[int] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    facebook_post_id: Optional[str] = Field(default=None)
    generation_metadata: Optional[Dict[str, Any]] = Field(default=None)
    hashtags: Optional[List[str]] = Field(default=None)
    impressions: Optional[int] = Field(default=None)
    initiative_id: UUID4
    instagram_post_id: Optional[str] = Field(default=None)
    is_published: Optional[bool] = Field(default=None)
    links: Optional[List[str]] = Field(default=None)
    media_metadata: Optional[Dict[str, Any]] = Field(default=None)
    media_urls: Optional[List[str]] = Field(default=None)
    post_type: str
    published_time: Optional[datetime.datetime] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    scheduled_time: Optional[datetime.datetime] = Field(default=None)
    shares: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    text_content: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class PostsInsert(CustomModelInsert):
    """Posts Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    ad_set_id: UUID4
    initiative_id: UUID4
    post_type: str
    
    # Optional fields
    clicks: Optional[int] = Field(default=None)
    comments_count: Optional[int] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    facebook_post_id: Optional[str] = Field(default=None)
    generation_metadata: Optional[Dict[str, Any]] = Field(default=None)
    hashtags: Optional[List[str]] = Field(default=None)
    impressions: Optional[int] = Field(default=None)
    instagram_post_id: Optional[str] = Field(default=None)
    is_published: Optional[bool] = Field(default=None)
    links: Optional[List[str]] = Field(default=None)
    media_metadata: Optional[Dict[str, Any]] = Field(default=None)
    media_urls: Optional[List[str]] = Field(default=None)
    published_time: Optional[datetime.datetime] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    scheduled_time: Optional[datetime.datetime] = Field(default=None)
    shares: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    text_content: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class PostsUpdate(CustomModelUpdate):
    """Posts Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    ad_set_id: Optional[UUID4] = Field(default=None)
    clicks: Optional[int] = Field(default=None)
    comments_count: Optional[int] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    facebook_post_id: Optional[str] = Field(default=None)
    generation_metadata: Optional[Dict[str, Any]] = Field(default=None)
    hashtags: Optional[List[str]] = Field(default=None)
    impressions: Optional[int] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    instagram_post_id: Optional[str] = Field(default=None)
    is_published: Optional[bool] = Field(default=None)
    links: Optional[List[str]] = Field(default=None)
    media_metadata: Optional[Dict[str, Any]] = Field(default=None)
    media_urls: Optional[List[str]] = Field(default=None)
    post_type: Optional[str] = Field(default=None)
    published_time: Optional[datetime.datetime] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    scheduled_time: Optional[datetime.datetime] = Field(default=None)
    shares: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    text_content: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class Posts(PostsBaseSchema):
    """Posts Schema for Pydantic."""
    pass


# Alias for backward compatibility
Post = Posts