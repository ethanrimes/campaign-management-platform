# agents/planner/models.py

"""
Planner agent models that extend and use centralized database models.
This module defines agent-specific structures while using database models for persistence.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal
from uuid import UUID, uuid4

# Import centralized database models
from backend.db.models.campaign import CampaignsInsert, CampaignsUpdate
from backend.db.models.ad_set import AdSetsInsert, AdSetsUpdate
from backend.db.models.serialization import serialize_dict, prepare_for_db


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
    """Budget allocation structure for agent use"""
    daily: Optional[float] = Field(None, description="Daily budget amount")
    lifetime: Optional[float] = Field(None, description="Lifetime budget amount")
    
    @validator('daily', 'lifetime')
    def validate_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Budget amounts must be positive")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format with Decimal"""
        result = {}
        if self.daily is not None:
            result['daily_budget'] = Decimal(str(self.daily))
        if self.lifetime is not None:
            result['lifetime_budget'] = Decimal(str(self.lifetime))
        return result


class Schedule(BaseModel):
    """Campaign/Ad Set schedule for agent use"""
    start_date: datetime = Field(description="Start date and time")
    end_date: datetime = Field(description="End date and time")
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format"""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


class TargetAudience(BaseModel):
    """Target audience configuration for agent use"""
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
    format_preferences: List[str] = Field(default_factory=list)
    key_messages: List[str] = Field(default_factory=list)
    visual_style: Optional[str] = Field(None)
    call_to_action: Optional[str] = Field(None)


class Materials(BaseModel):
    """Materials and assets for content creation"""
    links: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    brand_assets: List[str] = Field(default_factory=list)
    promo_codes: Optional[List[str]] = Field(None)
    landing_pages: Optional[List[str]] = Field(None)


class AgentAdSet(BaseModel):
    """Ad Set configuration for agent planning (wraps database model)"""
    id: str = Field(description="Ad set ID")
    name: str = Field(description="Ad set name")
    target_audience: TargetAudience = Field(description="Target audience configuration")
    placements: List[str] = Field(default=["ig_feed", "fb_feed"])
    budget: BudgetAllocation = Field(description="Budget allocation")
    bid_strategy: Optional[str] = Field(None)
    schedule: Optional[Schedule] = Field(None)
    post_frequency: int = Field(default=3, description="Posts per week")
    post_volume: int = Field(default=5, description="Total active posts")
    creative_brief: CreativeBrief = Field(description="Creative brief")
    materials: Materials = Field(description="Materials for content")
    
    def to_db_insert(self, campaign_id: UUID, initiative_id: UUID) -> AdSetsInsert:
        """Convert to database insert model"""
        data = {
            'id': UUID(self.id) if isinstance(self.id, str) else self.id,
            'campaign_id': campaign_id,
            'initiative_id': initiative_id,
            'name': self.name,
            'target_audience': serialize_dict(self.target_audience.dict()),
            'placements': serialize_dict({'platforms': self.placements}),
            'bid_strategy': self.bid_strategy,
            'post_frequency': self.post_frequency,
            'post_volume': self.post_volume,
            'creative_brief': serialize_dict(self.creative_brief.dict()),
            'materials': serialize_dict(self.materials.dict()),
            'status': 'active',
            'is_active': True
        }
        
        # Add budget fields
        budget_dict = self.budget.to_db_dict()
        data.update(budget_dict)
        
        # Add schedule fields if present
        if self.schedule:
            schedule_dict = self.schedule.to_db_dict()
            data['start_time'] = schedule_dict['start_date']
            data['end_time'] = schedule_dict['end_date']
        
        return AdSetsInsert(**data)


class AgentCampaign(BaseModel):
    """Campaign configuration for agent planning (wraps database model)"""
    id: str = Field(description="Campaign ID")
    name: str = Field(description="Campaign name")
    objective: CampaignObjective = Field(description="Campaign objective")
    description: Optional[str] = Field(None)
    budget_mode: BudgetMode = Field(default=BudgetMode.AD_SET_LEVEL)
    budget: BudgetAllocation = Field(description="Budget allocation")
    schedule: Schedule = Field(description="Campaign schedule")
    ad_sets: List[AgentAdSet] = Field(description="Ad sets in this campaign")
    
    def to_db_insert(self, initiative_id: UUID) -> CampaignsInsert:
        """Convert to database insert model"""
        data = {
            'id': UUID(self.id) if isinstance(self.id, str) else self.id,
            'initiative_id': initiative_id,
            'name': self.name,
            'objective': self.objective.value,
            'description': self.description,
            'budget_mode': self.budget_mode.value,
            'status': 'active',
            'is_active': True
        }
        
        # Add budget fields
        budget_dict = self.budget.to_db_dict()
        data.update(budget_dict)
        
        # Add schedule fields
        schedule_dict = self.schedule.to_db_dict()
        data['start_date'] = schedule_dict['start_date']
        data['end_date'] = schedule_dict['end_date']
        
        return CampaignsInsert(**data)


class OptimizationStrategy(BaseModel):
    """Optimization strategy details"""
    primary_metric: str = Field(description="Primary optimization metric")
    secondary_metrics: List[str] = Field(default_factory=list)
    allocation_method: str = Field(default="balanced")
    reasoning: str = Field(description="Explanation of strategy")


class PlannerOutput(BaseModel):
    """Main planner output structure for agent use"""
    campaigns: List[AgentCampaign] = Field(description="Campaign hierarchy")
    total_budget_allocated: float = Field(description="Total budget allocated")
    optimization_strategy: OptimizationStrategy = Field(description="Optimization approach")
    revision_notes: Optional[str] = Field(None)
    recommendations: Optional[List[str]] = Field(None)
    
    @validator('total_budget_allocated')
    def validate_total_budget(cls, v):
        if v < 0:
            raise ValueError("Total budget cannot be negative")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert entire output to database-ready format"""
        return serialize_dict(self.dict())
    
    async def save_to_db(self, db_client, initiative_id: UUID):
        """Save the planned campaigns and ad sets to database"""
        saved_campaigns = []
        
        for campaign in self.campaigns:
            # Save campaign
            campaign_insert = campaign.to_db_insert(initiative_id)
            saved_campaign = await db_client.insert("campaigns", campaign_insert.to_db_dict())
            saved_campaigns.append(saved_campaign)
            
            # Save ad sets for this campaign
            for ad_set in campaign.ad_sets:
                ad_set_insert = ad_set.to_db_insert(
                    campaign_id=UUID(campaign.id),
                    initiative_id=initiative_id
                )
                await db_client.insert("ad_sets", ad_set_insert.to_db_dict())
        
        return saved_campaigns


# Export the models that agents should use
__all__ = [
    'CampaignObjective',
    'BudgetMode',
    'BudgetAllocation',
    'Schedule',
    'TargetAudience',
    'CreativeBrief',
    'Materials',
    'AgentAdSet',
    'AgentCampaign',
    'OptimizationStrategy',
    'PlannerOutput'
]