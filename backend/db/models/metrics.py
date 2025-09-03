# backend/db/models/metrics.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4


class Metrics(BaseModel):
    """Performance metrics model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    entity_type: str  # campaign, ad_set, post
    entity_id: str
    
    # Metrics
    impressions: int = 0
    reach: int = 0
    engagement: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    
    # Calculated metrics
    ctr: Optional[float] = None  # Click-through rate
    cpc: Optional[float] = None  # Cost per click
    cpm: Optional[float] = None  # Cost per mille
    engagement_rate: Optional[float] = None
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Raw data
    raw_metrics: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
