# backend/db/models/ad_set.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4


class AdSet(BaseModel):
    """Ad Set model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    campaign_id: str
    
    # Ad Set Details
    name: str
    objective: Optional[str] = None
    
    # Targeting
    target_audience: Optional[Dict[str, Any]] = None  # Age, geo, interests, custom segments
    placements: Optional[List[str]] = None  # ["ig_feed", "ig_reels", "fb_stories"]
    
    # Budget & Schedule
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    spent_budget: float = 0.0
    bid_strategy: Optional[str] = None
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    schedule: Optional[Dict[str, Any]] = None  # Dayparting info
    
    # Content Strategy
    post_frequency: Optional[int] = None  # Posts per week
    post_volume: Optional[int] = None  # Total active posts
    creative_brief: Optional[Dict[str, Any]] = None  # Theme, tone, format hints
    materials: Optional[Dict[str, Any]] = None  # Links, hashtags, assets
    
    # Status
    status: str = "draft"  # draft, active, paused
    is_active: bool = True
    
    # Performance
    metrics: Optional[Dict[str, Any]] = None
    
    # Meta Ad Set ID
    meta_ad_set_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True