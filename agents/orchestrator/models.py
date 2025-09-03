# agents/orchestrator/models.py

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class CampaignObjective(str, Enum):
    """Campaign objective types"""
    AWARENESS = "AWARENESS"
    ENGAGEMENT = "ENGAGEMENT"
    TRAFFIC = "TRAFFIC"
    CONVERSIONS = "CONVERSIONS"


class BudgetMode(str, Enum):
    """Budget allocation modes"""
    CAMPAIGN_LEVEL = "campaign_level"
    AD_SET_LEVEL = "ad_set_level"


class BudgetAllocation(BaseModel):
    """Budget allocation structure"""
    daily: Optional[float] = Field(None, description="Daily budget amount")
    lifetime: Optional[float] = Field(None, description="Lifetime budget amount")
    
    @validator('daily', 'lifetime')
    def validate_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Budget amounts must be positive")
        return v


class Schedule(BaseModel):
    """Campaign/Ad Set schedule"""
    start_date: datetime = Field(description="Start date and time")
    end_date: datetime = Field(description="End date and time")
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v


class TargetAudience(BaseModel):
    """Target audience configuration"""
    age_range: List[int] = Field(default=[18, 65], min_items=2, max_items=2)
    locations: List[str] = Field(description="Geographic locations")
    interests: List[str] = Field(default_factory=list, description="Interest categories")
    languages: List[str] = Field(default=["English"], description="Target languages")
    custom_audiences: Optional[List[str]] = Field(None, description="Custom audience IDs")
    lookalike_audiences: Optional[List[str]] = Field(None, description="Lookalike audience IDs")
    
    @validator('age_range')
    def validate_age_range(cls, v):
        if v[0] < 13 or v[1] > 100:
            raise ValueError("Age range must be between 13 and 100")
        if v[0] >= v[1]:
            raise ValueError("Invalid age range")
        return v


class CreativeBrief(BaseModel):
    """Creative brief for content generation"""
    theme: str = Field(description="Content theme or topic")
    tone: str = Field(default="professional", description="Content tone")
    format_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred content formats (image, video, carousel)"
    )
    key_messages: List[str] = Field(default_factory=list, description="Key messages to convey")
    visual_style: Optional[str] = Field(None, description="Visual style guidelines")
    call_to_action: Optional[str] = Field(None, description="Primary CTA")


class Materials(BaseModel):
    """Materials and assets for content creation"""
    links: List[str] = Field(default_factory=list, description="Relevant URLs")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags to use")
    brand_assets: List[str] = Field(default_factory=list, description="Brand asset URLs")
    promo_codes: Optional[List[str]] = Field(None, description="Promotional codes")
    landing_pages: Optional[List[str]] = Field(None, description="Landing page URLs")


class AdSet(BaseModel):
    """Ad Set configuration"""
    id: str = Field(description="Ad set ID")
    name: str = Field(description="Ad set name")
    target_audience: TargetAudience = Field(description="Target audience configuration")
    placements: List[str] = Field(
        default=["ig_feed", "fb_feed"],
        description="Ad placements"
    )
    budget: BudgetAllocation = Field(description="Budget allocation")
    bid_strategy: Optional[str] = Field(None, description="Bidding strategy")
    schedule: Optional[Schedule] = Field(None, description="Ad set schedule")
    post_frequency: int = Field(default=3, description="Posts per week")
    post_volume: int = Field(default=5, description="Total active posts")
    creative_brief: CreativeBrief = Field(description="Creative brief")
    materials: Materials = Field(description="Materials for content")
    
    @validator('placements')
    def validate_placements(cls, v):
        valid_placements = [
            "ig_feed", "ig_stories", "ig_reels", 
            "fb_feed", "fb_stories", "fb_reels",
            "messenger_inbox", "audience_network"
        ]
        for placement in v:
            if placement not in valid_placements:
                raise ValueError(f"Invalid placement: {placement}")
        return v


class Campaign(BaseModel):
    """Campaign configuration"""
    id: str = Field(description="Campaign ID")
    name: str = Field(description="Campaign name")
    objective: CampaignObjective = Field(description="Campaign objective")
    description: Optional[str] = Field(None, description="Campaign description")
    budget_mode: BudgetMode = Field(
        default=BudgetMode.AD_SET_LEVEL,
        description="Budget allocation mode"
    )
    budget: BudgetAllocation = Field(description="Budget allocation")
    schedule: Schedule = Field(description="Campaign schedule")
    ad_sets: List[AdSet] = Field(description="Ad sets in this campaign")
    
    @validator('ad_sets')
    def validate_ad_sets(cls, v):
        if len(v) == 0:
            raise ValueError("Campaign must have at least one ad set")
        return v


class OptimizationStrategy(BaseModel):
    """Optimization strategy details"""
    primary_metric: str = Field(description="Primary optimization metric")
    secondary_metrics: List[str] = Field(default_factory=list, description="Secondary metrics")
    allocation_method: str = Field(
        default="balanced",
        description="Budget allocation method"
    )
    reasoning: str = Field(description="Explanation of strategy")


class OrchestratorOutput(BaseModel):
    """Main orchestrator output structure"""
    campaigns: List[Campaign] = Field(description="Campaign hierarchy")
    total_budget_allocated: float = Field(description="Total budget allocated")
    optimization_strategy: OptimizationStrategy = Field(description="Optimization approach")
    revision_notes: Optional[str] = Field(None, description="Notes on changes from previous plan")
    recommendations: Optional[List[str]] = Field(None, description="Strategic recommendations")
    
    @validator('total_budget_allocated')
    def validate_total_budget(cls, v):
        if v < 0:
            raise ValueError("Total budget cannot be negative")
        return v
    
    @validator('campaigns')
    def validate_budget_consistency(cls, v, values):
        if 'total_budget_allocated' in values:
            campaign_total = sum(
                c.budget.lifetime or 0 for c in v
            )
            if abs(campaign_total - values['total_budget_allocated']) > 0.01:
                raise ValueError("Campaign budgets don't match total allocated")
        return v