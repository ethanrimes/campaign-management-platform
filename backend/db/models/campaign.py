# backend/db/models/campaign.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4


class Campaign(BaseModel):
    """Campaign model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    initiative_id: str
    
    # Campaign Details
    name: str
    objective: str  # AWARENESS, ENGAGEMENT, TRAFFIC, CONVERSIONS
    description: Optional[str] = None
    
    # Budget
    budget_mode: Optional[str] = None  # campaign_level, ad_set_level
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    spent_budget: float = 0.0
    
    # Schedule
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Status
    status: str = "draft"  # draft, active, paused, completed
    is_active: bool = True
    
    # Performance
    metrics: Optional[Dict[str, Any]] = None  # Current performance metrics
    
    # Meta Campaign ID
    meta_campaign_id: Optional[str] = None  # Facebook/Instagram campaign ID
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True