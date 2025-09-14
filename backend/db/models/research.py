# backend/db/models/research.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any, List
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class ResearchBaseSchema(CustomModel):
    """Research Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    created_at: Optional[datetime.datetime] = Field(default=None)
    expires_at: Optional[datetime.datetime] = Field(default=None)
    initiative_id: UUID4
    insights: Optional[List[Dict[str, Any]]] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)
    relevance_score: Optional[Dict[str, Any]] = Field(default=None)
    research_type: str
    search_queries: Optional[List[str]] = Field(default=None)
    sources: Optional[List[str]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    topic: str


class ResearchInsert(CustomModelInsert):
    """Research Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    initiative_id: UUID4
    research_type: str
    topic: str
    
    # Optional fields
    created_at: Optional[datetime.datetime] = Field(default=None)
    expires_at: Optional[datetime.datetime] = Field(default=None)
    insights: Optional[List[Dict[str, Any]]] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)
    relevance_score: Optional[Dict[str, Any]] = Field(default=None)
    search_queries: Optional[List[str]] = Field(default=None)
    sources: Optional[List[str]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class ResearchUpdate(CustomModelUpdate):
    """Research Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    expires_at: Optional[datetime.datetime] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    insights: Optional[List[Dict[str, Any]]] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)
    relevance_score: Optional[Dict[str, Any]] = Field(default=None)
    research_type: Optional[str] = Field(default=None)
    search_queries: Optional[List[str]] = Field(default=None)
    sources: Optional[List[str]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    topic: Optional[str] = Field(default=None)


class Research(ResearchBaseSchema):
    """Research Schema for Pydantic."""
    pass