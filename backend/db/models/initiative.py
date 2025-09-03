
# backend/db/models/initiative.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4

class Initiative(BaseModel):
    """Initiative/Presence model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    name: str
    description: Optional[str] = None
    
    # Social Media Accounts
    facebook_page_id: Optional[str] = None
    facebook_page_name: Optional[str] = None
    facebook_page_url: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_account_id: Optional[str] = None
    instagram_url: Optional[str] = None
    
    # Configuration
    category: Optional[str] = None  # Education, Nonprofit, etc.
    objectives: Optional[Dict[str, Any]] = None  # KPIs and goals
    brand_assets: Optional[Dict[str, Any]] = None  # Links to logos, images, etc.
    custom_prompts: Optional[Dict[str, Any]] = None  # Initiative-specific prompt overrides
    
    # Budget
    daily_budget: Optional[Dict[str, Any]] = None  # {"amount": 100, "currency": "USD"}
    total_budget: Optional[Dict[str, Any]] = None  # {"amount": 10000, "currency": "USD"}
    
    # Model Configuration
    model_provider: str = "openai"  # openai, grok, gemini, anthropic
    llm_config: Optional[Dict[str, Any]] = None  # Model-specific settings (renamed from model_config)
    
    # Metrics Goals
    optimization_metric: Optional[str] = None  # reach, engagement, conversions
    target_metrics: Optional[Dict[str, Any]] = None  # {"reach": 10000, "engagement_rate": 0.05}
    
    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional Settings
    settings: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True