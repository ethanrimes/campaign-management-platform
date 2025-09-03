# backend/db/models/research.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4


class Research(BaseModel):
    """Research data model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    initiative_id: str
    
    # Research Details
    research_type: str  # competitor, trend, hashtag, audience
    topic: str
    
    # Content
    summary: Optional[str] = None
    insights: Optional[List[Dict[str, Any]]] = None  # Structured insights
    raw_data: Optional[Dict[str, Any]] = None  # Raw search results
    
    # Sources
    sources: Optional[List[str]] = None  # List of URLs and references
    search_queries: Optional[List[str]] = None  # Queries used
    
    # Relevance
    relevance_score: Optional[Dict[str, Any]] = None  # Scoring for different aspects
    tags: Optional[List[str]] = None  # Categorization tags
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # When research becomes stale
    
    class Config:
        orm_mode = True