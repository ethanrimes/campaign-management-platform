# backend/db/models/metrics.py

from decimal import Decimal
from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class MetricsBaseSchema(CustomModel):
    """Metrics Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    clicks: Optional[int] = Field(default=None)
    conversions: Optional[int] = Field(default=None)
    cpc: Optional[Decimal] = Field(default=None)
    cpm: Optional[Decimal] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    ctr: Optional[Decimal] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    engagement_rate: Optional[Decimal] = Field(default=None)
    entity_id: UUID4
    entity_type: str
    impressions: Optional[int] = Field(default=None)
    initiative_id: UUID4
    period_end: datetime.datetime
    period_start: datetime.datetime
    raw_metrics: Optional[Dict[str, Any]] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    spend: Optional[Decimal] = Field(default=None)


class MetricsInsert(CustomModelInsert):
    """Metrics Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    entity_id: UUID4
    entity_type: str
    initiative_id: UUID4
    period_end: datetime.datetime
    period_start: datetime.datetime
    
    # Optional fields
    clicks: Optional[int] = Field(default=None)
    conversions: Optional[int] = Field(default=None)
    cpc: Optional[Decimal] = Field(default=None)
    cpm: Optional[Decimal] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    ctr: Optional[Decimal] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    engagement_rate: Optional[Decimal] = Field(default=None)
    impressions: Optional[int] = Field(default=None)
    raw_metrics: Optional[Dict[str, Any]] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    spend: Optional[Decimal] = Field(default=None)


class MetricsUpdate(CustomModelUpdate):
    """Metrics Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    clicks: Optional[int] = Field(default=None)
    conversions: Optional[int] = Field(default=None)
    cpc: Optional[Decimal] = Field(default=None)
    cpm: Optional[Decimal] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    ctr: Optional[Decimal] = Field(default=None)
    engagement: Optional[int] = Field(default=None)
    engagement_rate: Optional[Decimal] = Field(default=None)
    entity_id: Optional[UUID4] = Field(default=None)
    entity_type: Optional[str] = Field(default=None)
    impressions: Optional[int] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    period_end: Optional[datetime.datetime] = Field(default=None)
    period_start: Optional[datetime.datetime] = Field(default=None)
    raw_metrics: Optional[Dict[str, Any]] = Field(default=None)
    reach: Optional[int] = Field(default=None)
    spend: Optional[Decimal] = Field(default=None)


class Metrics(MetricsBaseSchema):
    """Metrics Schema for Pydantic."""
    pass