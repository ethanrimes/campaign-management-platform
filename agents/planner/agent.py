# agents/planner/agent.py

"""
Planning Agent for campaign management.
Handles campaign planning, budget allocation, and ad set creation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from agents.planner.models import (
    PlannerOutput, Campaign, AdSet, BudgetAllocation,
    Schedule, TargetAudience, CreativeBrief, Materials,
    OptimizationStrategy, CampaignObjective
)
from agents.planner.context_manager import PlannerContextManager
from agents.planner.validation import OutputValidator, BudgetValidator
from backend.db.supabase_client import DatabaseClient
import uuid
import json
import logging

logger = logging.getLogger(__name__)

# Fallback dates for when parsing fails - clearly identifiable as placeholders
FALLBACK_START_DATE = datetime(2000, 1, 1, 0, 0, 0)
FALLBACK_END_DATE = datetime(2000, 1, 31, 0, 0, 0)


class PlanningAgent(BaseAgent):
    """Planning agent for campaign strategy and budget allocation"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.context_manager = PlannerContextManager(config.initiative_id)
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize planner-specific tools"""
        return []
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for planning with grounding emphasis"""
        try:
            with open("agents/planner/prompts/system_prompt.txt", "r") as f:
                base_prompt = f.read()
        except:
            base_prompt = """You are an expert marketing campaign planner AI. 
            Ground all decisions in provided research data."""
        
        schema_prompt = """
        
        You must return your response as a valid JSON object that conforms to this exact schema:
        {
            "campaigns": [
                {
                    "id": "unique-id",
                    "name": "Campaign Name",
                    "objective": "AWARENESS|ENGAGEMENT|TRAFFIC|CONVERSIONS",
                    "description": "Optional description explaining research connection",
                    "budget_mode": "campaign_level|ad_set_level",
                    "budget": {
                        "daily": 100.0,
                        "lifetime": 3000.0
                    },
                    "schedule": {
                        "start_date": "ISO datetime",
                        "end_date": "ISO datetime"
                    },
                    "ad_sets": [
                        {
                            "id": "unique-id",
                            "name": "Ad Set Name",
                            "target_audience": {
                                "age_range": [18, 65],
                                "locations": ["location1"],
                                "interests": ["from_research"],
                                "languages": ["English"]
                            },
                            "placements": ["ig_feed", "fb_feed"],
                            "budget": {
                                "daily": 50.0,
                                "lifetime": 1500.0
                            },
                            "creative_brief": {
                                "theme": "From research opportunities",
                                "tone": "professional|casual|friendly",
                                "format_preferences": ["image", "video"],
                                "key_messages": ["from_research_insights"]
                            },
                            "materials": {
                                "links": ["ONLY_FROM_VALIDATED_LINKS"],
                                "hashtags": ["#from_research"],
                                "brand_assets": []
                            },
                            "post_frequency": 3,
                            "post_volume": 5
                        }
                    ]
                }
            ],
            "total_budget_allocated": 3000.0,
            "optimization_strategy": {
                "primary_metric": "from_initiative_settings",
                "secondary_metrics": ["metric1"],
                "allocation_method": "balanced|aggressive|conservative",
                "reasoning": "Explanation referencing research"
            },
            "revision_notes": "Notes on research grounding",
            "recommendations": ["research_based_recommendation"]
        }
        
        CRITICAL: All materials.links MUST come from the validated_links list provided.
        """
        
        return base_prompt + schema_prompt
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the planning agent with research grounding and validation"""
        logger.info("\n" + "="*70)
        logger.info("PLANNING AGENT EXECUTION STARTED")
        logger.info("="*70)
        
        # Gather comprehensive context including research
        logger.info("\n📊 PHASE 1: GATHERING CONTEXT")
        context = await self.context_manager.gather_context(input_data)
        
        # Create planning prompt with research emphasis
        logger.info("\n🎯 PHASE 2: CREATING RESEARCH-GROUNDED PROMPT")
        prompt = self.context_manager.create_planning_prompt(context)
        
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        # Get model config
        from backend.config.settings import settings
        model_config = self.config.llm_config or self._load_model_config()
        
        # Call OpenAI API for campaign planning
        logger.info("\n🤖 PHASE 3: GENERATING CAMPAIGN PLAN")
        response = self.client.chat.completions.create(
            model=model_config.model_name,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            response_format={"type": "json_object"}
        )
        
        # Parse response into Pydantic model
        raw_output = json.loads(response.choices[0].message.content)
        logger.info("\n🔍 PHASE 4: PARSING AND VALIDATING OUTPUT")
        
        # Convert to Pydantic models for validation
        planner_output = self._parse_to_pydantic(raw_output, context)
        
        # Validate output against research data
        logger.info("\n🔍 PHASE 5: VALIDATING AGAINST RESEARCH")
        validator = OutputValidator(context)
        planner_output = validator.validate_and_fix_output(planner_output)
        
        # Validate budget allocation
        budget_valid, budget_msg = BudgetValidator.validate_budget_allocation(
            planner_output,
            context["budget"]["total"]
        )
        logger.info(f"\n💰 Budget validation: {budget_msg}")
        
        if not budget_valid:
            planner_output = self._adjust_budget(planner_output, context["budget"]["total"])
        
        # Save the plan to database - ensure JSON serializable
        plan_dict = planner_output.dict()
        await self.save_plan(self._make_json_serializable(plan_dict))
        
        logger.info("\n" + "="*70)
        logger.info("PLANNING EXECUTION COMPLETE")
        logger.info("="*70)
        
        return planner_output.dict()
    
    def _parse_to_pydantic(self, raw_output: Dict[str, Any], context: Dict[str, Any]) -> PlannerOutput:
        """Parse raw output into Pydantic models with validation"""
        campaigns = []
        for camp_data in raw_output.get("campaigns", []):
            ad_sets = []
            for ad_set_data in camp_data.get("ad_sets", []):
                ad_set_id = ad_set_data.get("id", str(uuid.uuid4()))
                ad_set = AdSet(
                    id=self._ensure_valid_uuid(ad_set_id),
                    name=ad_set_data["name"],
                    target_audience=TargetAudience(**ad_set_data.get("target_audience", {
                        "age_range": [18, 65],
                        "locations": ["United States"],
                        "interests": [],
                        "languages": ["English"]
                    })),
                    placements=ad_set_data.get("placements", ["ig_feed", "fb_feed"]),
                    budget=BudgetAllocation(**ad_set_data.get("budget", {})),
                    creative_brief=CreativeBrief(**ad_set_data.get("creative_brief", {
                        "theme": "General",
                        "tone": "professional"
                    })),
                    materials=Materials(**ad_set_data.get("materials", {})),
                    post_frequency=ad_set_data.get("post_frequency", 3),
                    post_volume=ad_set_data.get("post_volume", 5)
                )
                ad_sets.append(ad_set)
            
            campaign_id = camp_data.get("id", str(uuid.uuid4()))
            campaign = Campaign(
                id=self._ensure_valid_uuid(campaign_id),
                name=camp_data["name"],
                objective=CampaignObjective(camp_data["objective"]),
                description=camp_data.get("description"),
                budget=BudgetAllocation(**camp_data.get("budget", {})),
                schedule=self._parse_schedule(camp_data.get("schedule", {})),
                ad_sets=ad_sets
            )
            campaigns.append(campaign)
        
        opt_strategy = OptimizationStrategy(
            primary_metric=raw_output.get("optimization_strategy", {}).get("primary_metric", "reach"),
            secondary_metrics=raw_output.get("optimization_strategy", {}).get("secondary_metrics", []),
            allocation_method=raw_output.get("optimization_strategy", {}).get("allocation_method", "balanced"),
            reasoning=raw_output.get("optimization_strategy", {}).get("reasoning", "Default strategy")
        )
        
        output = PlannerOutput(
            campaigns=campaigns,
            total_budget_allocated=raw_output.get("total_budget_allocated", 0),
            optimization_strategy=opt_strategy,
            revision_notes=raw_output.get("revision_notes"),
            recommendations=raw_output.get("recommendations", [])
        )
        
        return output
    
    def _parse_schedule(self, schedule_data: Dict[str, Any]) -> Schedule:
        """Parse schedule data with fallback dates for invalid formats"""
        # Parse start date with fallback
        try:
            start_date_str = schedule_data.get("start_date", "")
            if not start_date_str or start_date_str == "N/A":
                raise ValueError("Missing or invalid start_date")
            start_date = datetime.fromisoformat(start_date_str)
        except (ValueError, KeyError, TypeError):
            start_date = FALLBACK_START_DATE
            logger.warning(f"Invalid start_date '{schedule_data.get('start_date')}', using fallback: {FALLBACK_START_DATE}")
        
        # Parse end date with fallback
        try:
            end_date_str = schedule_data.get("end_date", "")
            if not end_date_str or end_date_str == "N/A":
                raise ValueError("Missing or invalid end_date")
            end_date = datetime.fromisoformat(end_date_str)
        except (ValueError, KeyError, TypeError):
            end_date = FALLBACK_END_DATE
            logger.warning(f"Invalid end_date '{schedule_data.get('end_date')}', using fallback: {FALLBACK_END_DATE}")
        
        return Schedule(start_date=start_date, end_date=end_date)
    
    def _make_json_serializable(self, data: Any) -> Any:
        """Convert data to be JSON serializable, handling datetime objects"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        else:
            return data
    
    def _ensure_valid_uuid(self, id_value: str) -> str:
        """Ensure the ID is a valid UUID, generate new one if not"""
        import re
        
        # Check if it's already a valid UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, str(id_value).lower()):
            return str(id_value)
        
        # Generate new UUID if invalid format
        new_uuid = str(uuid.uuid4())
        logger.warning(f"Invalid ID format '{id_value}', generated new UUID: {new_uuid}")
        return new_uuid
    
    def _adjust_budget(self, output: PlannerOutput, total_budget: float) -> PlannerOutput:
        """Adjust budget allocation if needed"""
        actual_total = sum(
            campaign.budget.lifetime or 0 
            for campaign in output.campaigns
        )
        
        if actual_total > total_budget:
            scale_factor = total_budget / actual_total
            
            for campaign in output.campaigns:
                if campaign.budget.lifetime:
                    campaign.budget.lifetime *= scale_factor
                if campaign.budget.daily:
                    campaign.budget.daily *= scale_factor
                
                for ad_set in campaign.ad_sets:
                    if ad_set.budget.lifetime:
                        ad_set.budget.lifetime *= scale_factor
                    if ad_set.budget.daily:
                        ad_set.budget.daily *= scale_factor
            
            output.total_budget_allocated = total_budget
            if output.revision_notes:
                output.revision_notes += " Budget scaled to fit constraints."
            else:
                output.revision_notes = "Budget scaled to fit constraints."
        
        return output
    
    def validate_output(self, output: Any) -> bool:
        """Validate planner output using Pydantic"""
        if not isinstance(output, dict):
            return False
        
        try:
            PlannerOutput(**output)
            return True
        except Exception as e:
            logger.error(f"Output validation error: {e}")
            return False
    
    async def save_plan(self, plan: Dict[str, Any]):
        """Save the campaign plan to database"""
        logger.info("\n💾 SAVING CAMPAIGN PLAN TO DATABASE...")
        
        execution_id = getattr(self, 'execution_id', None)
        execution_step = getattr(self, 'execution_step', 'Planning')
        
        if execution_id:
            logger.info(f"Using execution_id: {execution_id}")
        
        # Save plan metadata
        plan_entry = {
            "initiative_id": self.config.initiative_id,
            "plan_type": "campaign_hierarchy",
            "plan_data": plan,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in a plans table or as part of campaigns
        for campaign_data in plan["campaigns"]:
            # Ensure dates are properly serialized
            schedule_data = campaign_data.get("schedule", {})
            start_date = schedule_data.get("start_date")
            end_date = schedule_data.get("end_date")
            
            # Convert datetime objects to ISO strings if needed
            if isinstance(start_date, datetime):
                start_date = start_date.isoformat()
            if isinstance(end_date, datetime):
                end_date = end_date.isoformat()
            
            campaign_entry = {
                "id": campaign_data["id"],
                "initiative_id": self.config.initiative_id,
                "name": campaign_data["name"],
                "objective": campaign_data["objective"],
                "daily_budget": campaign_data.get("budget", {}).get("daily"),
                "lifetime_budget": campaign_data.get("budget", {}).get("lifetime"),
                "start_date": start_date,
                "end_date": end_date,
                "status": "draft",
                "is_active": True,
                # Add execution tracking
                "execution_id": execution_id,
                "execution_metadata": {
                    "step": execution_step,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            await self.db_client.insert("campaigns", campaign_entry)
            logger.info(f"  ✔ Saved campaign: {campaign_data['name']}")
            
            for ad_set_data in campaign_data.get("ad_sets", []):
                ad_set_entry = {
                    "id": ad_set_data["id"],
                    "initiative_id": self.config.initiative_id,
                    "campaign_id": campaign_data["id"],
                    "name": ad_set_data["name"],
                    "target_audience": ad_set_data.get("target_audience"),
                    "placements": ad_set_data.get("placements"),
                    "daily_budget": ad_set_data.get("budget", {}).get("daily"),
                    "lifetime_budget": ad_set_data.get("budget", {}).get("lifetime"),
                    "creative_brief": ad_set_data.get("creative_brief"),
                    "materials": ad_set_data.get("materials"),
                    "post_frequency": ad_set_data.get("post_frequency"),
                    "post_volume": ad_set_data.get("post_volume"),
                    "status": "draft",
                    "is_active": True,
                    # Add execution tracking
                    "execution_id": execution_id,
                    "execution_step": execution_step
                }
                
                await self.db_client.insert("ad_sets", ad_set_entry)
                logger.info(f"    ✔ Saved ad set: {ad_set_data['name']}")
        
        logger.info("✅ Campaign plan saved successfully!")