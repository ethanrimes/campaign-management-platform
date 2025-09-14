# backend/db/models/media_file.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class MediaFilesBaseSchema(CustomModel):
    """MediaFiles Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    created_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was created")
    dimensions: Optional[Dict[str, int]] = Field(default=None, description="JSON with width/height for images/videos")
    duration_seconds: Optional[int] = Field(default=None, description="Duration for video files")
    file_size_bytes: Optional[int] = Field(default=None, description="File size in bytes")
    file_type: str = Field(description="Type of media: image, video, reel")
    initiative_id: UUID4
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata as JSON")
    prompt_used: Optional[str] = Field(default=None, description="AI prompt used to generate the media")
    public_url: str = Field(description="Public URL for accessing the file")
    supabase_path: str = Field(description="Path in Supabase storage bucket")
    updated_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was last updated")


class MediaFilesInsert(CustomModelInsert):
    """MediaFiles Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    file_type: str = Field(description="Type of media: image, video, reel")
    initiative_id: UUID4
    public_url: str = Field(description="Public URL for accessing the file")
    supabase_path: str = Field(description="Path in Supabase storage bucket")
    
    # Optional fields
    created_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was created")
    dimensions: Optional[Dict[str, int]] = Field(default=None, description="JSON with width/height for images/videos")
    duration_seconds: Optional[int] = Field(default=None, description="Duration for video files")
    file_size_bytes: Optional[int] = Field(default=None, description="File size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata as JSON")
    prompt_used: Optional[str] = Field(default=None, description="AI prompt used to generate the media")
    updated_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was last updated")


class MediaFilesUpdate(CustomModelUpdate):
    """MediaFiles Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was created")
    dimensions: Optional[Dict[str, int]] = Field(default=None, description="JSON with width/height for images/videos")
    duration_seconds: Optional[int] = Field(default=None, description="Duration for video files")
    file_size_bytes: Optional[int] = Field(default=None, description="File size in bytes")
    file_type: Optional[str] = Field(default=None, description="Type of media: image, video, reel")
    initiative_id: Optional[UUID4] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata as JSON")
    prompt_used: Optional[str] = Field(default=None, description="AI prompt used to generate the media")
    public_url: Optional[str] = Field(default=None, description="Public URL for accessing the file")
    supabase_path: Optional[str] = Field(default=None, description="Path in Supabase storage bucket")
    updated_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp when the record was last updated")


class MediaFiles(MediaFilesBaseSchema):
    """MediaFiles Schema for Pydantic."""
    pass