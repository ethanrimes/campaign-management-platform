# backend/db/models/initiative.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional, Dict, Any
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class InitiativesBaseSchema(CustomModel):
    """Initiatives Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    brand_assets: Optional[Dict[str, Any]] = Field(default=None)
    category: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    custom_prompts: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Dict[str, Any]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    encrypted_tokens: Optional[Dict[str, Any]] = Field(default=None)
    facebook_page_id: Optional[str] = Field(default=None)
    facebook_page_name: Optional[str] = Field(default=None)
    facebook_page_url: Optional[str] = Field(default=None)
    model_provider: Optional[str] = Field(default=None, alias="field_model_provider")
    instagram_account_id: Optional[str] = Field(default=None)
    instagram_business_id: Optional[str] = Field(default=None, description="Instagram Business Account ID for the initiative")
    instagram_url: Optional[str] = Field(default=None)
    instagram_username: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    llm_config: Optional[Dict[str, Any]] = Field(default=None)
    name: str
    objectives: Optional[Dict[str, Any]] = Field(default=None)
    optimization_metric: Optional[str] = Field(default=None)
    settings: Optional[Dict[str, Any]] = Field(default=None)
    target_metrics: Optional[Dict[str, Any]] = Field(default=None)
    tokens_metadata: Optional[Dict[str, Any]] = Field(default=None)
    total_budget: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class InitiativesInsert(CustomModelInsert):
    """Initiatives Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    name: str
    
    # Optional fields
    brand_assets: Optional[Dict[str, Any]] = Field(default=None)
    category: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    custom_prompts: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Dict[str, Any]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    encrypted_tokens: Optional[Dict[str, Any]] = Field(default=None)
    facebook_page_id: Optional[str] = Field(default=None)
    facebook_page_name: Optional[str] = Field(default=None)
    facebook_page_url: Optional[str] = Field(default=None)
    model_provider: Optional[str] = Field(default=None, alias="field_model_provider")
    instagram_account_id: Optional[str] = Field(default=None)
    instagram_business_id: Optional[str] = Field(default=None, description="Instagram Business Account ID for the initiative")
    instagram_url: Optional[str] = Field(default=None)
    instagram_username: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    llm_config: Optional[Dict[str, Any]] = Field(default=None)
    objectives: Optional[Dict[str, Any]] = Field(default=None)
    optimization_metric: Optional[str] = Field(default=None)
    settings: Optional[Dict[str, Any]] = Field(default=None)
    target_metrics: Optional[Dict[str, Any]] = Field(default=None)
    tokens_metadata: Optional[Dict[str, Any]] = Field(default=None)
    total_budget: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class InitiativesUpdate(CustomModelUpdate):
    """Initiatives Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    brand_assets: Optional[Dict[str, Any]] = Field(default=None)
    category: Optional[str] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    custom_prompts: Optional[Dict[str, Any]] = Field(default=None)
    daily_budget: Optional[Dict[str, Any]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    encrypted_tokens: Optional[Dict[str, Any]] = Field(default=None)
    facebook_page_id: Optional[str] = Field(default=None)
    facebook_page_name: Optional[str] = Field(default=None)
    facebook_page_url: Optional[str] = Field(default=None)
    model_provider: Optional[str] = Field(default=None, alias="field_model_provider")
    instagram_account_id: Optional[str] = Field(default=None)
    instagram_business_id: Optional[str] = Field(default=None, description="Instagram Business Account ID for the initiative")
    instagram_url: Optional[str] = Field(default=None)
    instagram_username: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    llm_config: Optional[Dict[str, Any]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    objectives: Optional[Dict[str, Any]] = Field(default=None)
    optimization_metric: Optional[str] = Field(default=None)
    settings: Optional[Dict[str, Any]] = Field(default=None)
    target_metrics: Optional[Dict[str, Any]] = Field(default=None)
    tokens_metadata: Optional[Dict[str, Any]] = Field(default=None)
    total_budget: Optional[Dict[str, Any]] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class Initiatives(InitiativesBaseSchema):
    """Initiatives Schema for Pydantic."""
    pass


# Alias for backward compatibility
Initiative = Initiatives