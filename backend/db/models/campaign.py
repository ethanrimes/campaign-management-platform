# backend/db/models/campaign.py

from decimal import Decimal
from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class CampaignsBaseSchema(CustomModel):
    """Campaigns Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    budget_mode: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    description: Optional[str] = Field(default=None)
    end_date: Optional[datetime.datetime] = Field(default=None)
    initiative_id: UUID4
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    meta_campaign_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    name: str
    objective: str
    spent_budget: Optional[Decimal] = Field(default=None)
    start_date: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class CampaignsInsert(CustomModelInsert):
    """Campaigns Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    initiative_id: UUID4
    name: str
    objective: str
    
    # Optional fields
    budget_mode: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    description: Optional[str] = Field(default=None)
    end_date: Optional[datetime.datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    meta_campaign_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    spent_budget: Optional[Decimal] = Field(default=None)
    start_date: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class CampaignsUpdate(CustomModelUpdate):
    """Campaigns Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    budget_mode: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    daily_budget: Optional[Decimal] = Field(default=None)
    description: Optional[str] = Field(default=None)
    end_date: Optional[datetime.datetime] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    lifetime_budget: Optional[Decimal] = Field(default=None)
    meta_campaign_id: Optional[str] = Field(default=None)
    metrics: Optional[Dict[str, Any]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    objective: Optional[str] = Field(default=None)
    spent_budget: Optional[Decimal] = Field(default=None)
    start_date: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class Campaigns(CampaignsBaseSchema):
    """Campaigns Schema for Pydantic."""
    pass


# Alias for backward compatibility
Campaign = Campaigns