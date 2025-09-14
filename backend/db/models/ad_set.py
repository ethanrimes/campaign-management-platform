# backend/db/models/ad_set.py

from decimal import Decimal
from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any, List
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class AdSetsBaseSchema(CustomModel):
    """AdSets Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    bid_strategy: Optional[str] = Field(default=None)
    campaign_id: UUID4
    created_at: Optional[datetime.datetime] = Field(default=None)
    creative_brief: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    end_time: Optional[datetime.datetime] = Field(default=None)
    initiative_id: UUID4
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    materials: Optional[Dict[str, Any]] = Field(default=None)
    meta_ad_set_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    name: str
    objective: Optional[str] = Field(default=None)
    placements: Optional[Dict[str, Any]] = Field(default=None)
    post_frequency: Optional[int] = Field(default=None)
    post_volume: Optional[int] = Field(default=None)
    schedule: Optional[Dict[str, Any]] = Field(default=None)
    spent_budget: Optional[Decimal] = Field(default=None)
    start_time: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    target_audience: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class AdSetsInsert(CustomModelInsert):
    """AdSets Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    campaign_id: UUID4
    initiative_id: UUID4
    name: str
    
    # Optional fields
    bid_strategy: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    creative_brief: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    end_time: Optional[datetime.datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    materials: Optional[Dict[str, Any]] = Field(default=None)
    meta_ad_set_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    objective: Optional[str] = Field(default=None)
    placements: Optional[Dict[str, Any]] = Field(default=None)
    post_frequency: Optional[int] = Field(default=None)
    post_volume: Optional[int] = Field(default=None)
    schedule: Optional[Dict[str, Any]] = Field(default=None)
    spent_budget: Optional[Decimal] = Field(default=None)
    start_time: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    target_audience: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class AdSetsUpdate(CustomModelUpdate):
    """AdSets Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    bid_strategy: Optional[str] = Field(default=None)
    campaign_id: Optional[UUID4] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    creative_brief: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    end_time: Optional[datetime.datetime] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    materials: Optional[Dict[str, Any]] = Field(default=None)
    meta_ad_set_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    objective: Optional[str] = Field(default=None)
    placements: Optional[Dict[str, Any]] = Field(default=None)
    post_frequency: Optional[int] = Field(default=None)
    post_volume: Optional[int] = Field(default=None)
    schedule: Optional[Dict[str, Any]] = Field(default=None)
    spent_budget: Optional[Decimal] = Field(default=None)
    start_time: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    target_audience: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class AdSets(AdSetsBaseSchema):
    """AdSets Schema for Pydantic."""
    pass


# Alias for backward compatibility
AdSet = AdSets