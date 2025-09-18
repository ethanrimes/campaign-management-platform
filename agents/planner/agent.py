# agents/planner/agent.py

from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel
from agents.base.agent import BaseAgent, AgentConfig
from agents.planner.models import PlannerOutput
from agents.planner.prompt_builder import PlannerPromptBuilder
from backend.db.supabase_client import DatabaseClient
from agents.guardrails.validators import PlannerValidator
from agents.guardrails.initiative_loader import InitiativeLoader
from backend.config.settings import settings
from uuid import UUID
import uuid
import logging

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """Planning agent with structured output and guardrails"""
    
    def __init__(self, config: AgentConfig):
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.prompt_builder = PlannerPromptBuilder(config.initiative_id)
        self.validator = PlannerValidator()
        self.initiative_loader = InitiativeLoader(config.initiative_id)
        super().__init__(config)
    
    def _initialize_tools(self) -> List[Any]:
        """No external tools needed for planning"""
        return []
    
    def get_output_model(self) -> Type[BaseModel]:
        """Return the PlannerOutput model for structured output"""
        return PlannerOutput
    
    def get_system_prompt(self) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.get_system_prompt()
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build user prompt with planning context"""
        # Extract from fresh context that BaseAgent added
        context = input_data.get("context", {})
        research_resources = input_data.get("research_resources", {})
        
        # Get initiative and budget from fresh context
        initiative = context.get("initiative", {})
        budget = {
            "daily": initiative.get("daily_budget", {}).get("amount", settings.DEFAULT_DAILY_BUDGET),
            "total": initiative.get("total_budget", {}).get("amount", settings.DEFAULT_CAMPAIGN_BUDGET)
        }
        
        # Use fresh statistics from context
        stats = context.get("statistics", {})
        
        # Pass to prompt builder with fresh data
        enhanced_input = {
            "context": context,
            "research_resources": research_resources,
            "budget": budget,
            "initiative": initiative
        }
        
        return self.prompt_builder.build_user_prompt(enhanced_input, error_feedback)
    
    def _sanitize_llm_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate all UUIDs for planner output"""
        import uuid
        
        # Fix campaigns and ad_sets
        if "campaigns" in output:
            for campaign in output["campaigns"]:
                # Generate proper campaign ID
                campaign["id"] = str(uuid.uuid4())
                
                # Fix ad_sets within each campaign
                if "ad_sets" in campaign:
                    for ad_set in campaign["ad_sets"]:
                        ad_set["id"] = str(uuid.uuid4())
        
        return output

    def validate_output(self, output: Any) -> bool:
        """Validate output structure"""
        if not isinstance(output, dict):
            return False
        
        # Check required fields for PlannerOutput
        required_fields = ["campaigns", "total_budget_allocated", "optimization_strategy"]
        if not all(field in output for field in required_fields):
            return False
        
        # Check campaigns structure
        campaigns = output.get("campaigns", [])
        if not isinstance(campaigns, list) or len(campaigns) == 0:
            return False
        
        return True
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planning workflow with guardrails."""
        logger.info("\n" + "=" * 70)
        logger.info("PLANNING AGENT STARTING (WITH GUARDRAILS)")
        logger.info("=" * 70)
        
        # STEP 1: Deactivate existing campaigns first
        await self.deactivate_existing_campaigns_and_ad_sets()
        
        # STEP 2: No need to load context here - execute_with_retries will do it
        
        # STEP 3: Extract research results if available
        research_results = input_data.get("research_results", {})
        
        # Build research resources
        research_resources = {
            "validated_links": research_results.get("sources", []),
            "validated_hashtags": research_results.get("recommended_hashtags", []),
            "opportunities": research_results.get("content_opportunities", [])
        }
        
        # STEP 4: Prepare structured input (context will be added in execute_with_retries)
        planning_input = {
            "research_results": research_results,
            "research_resources": research_resources,
            # Don't need to add context here - base class will handle it
        }
        
        # STEP 5: Call execute_with_retries (will fetch fresh context)
        result = await self.execute_with_retries(planning_input)
        
        # STEP 6: Save the validated plan to database
        saved_campaigns = await self.save_plan(result)
        
        # CRITICAL: Return the saved campaigns with their database IDs
        result["campaigns"] = saved_campaigns
        
        logger.info("✅ Planning completed with guardrail validation and database persistence")
        return result
    
    async def deactivate_existing_campaigns_and_ad_sets(self):
        """Deactivate all existing campaigns and ad sets"""
        logger.info("DEACTIVATING EXISTING CAMPAIGNS")
        
        # Deactivate campaigns
        campaigns = await self.db_client.select(
            "campaigns",
            filters={"initiative_id": self.config.initiative_id}
        )
        
        for campaign in campaigns:
            if campaign.get("is_active"):
                await self.db_client.update(
                    "campaigns",
                    data={"is_active": False, "status": "archived"},
                    filters={"id": campaign["id"]}
                )
        
        # Deactivate ad sets
        ad_sets = await self.db_client.select(
            "ad_sets",
            filters={"initiative_id": self.config.initiative_id}
        )
        
        for ad_set in ad_sets:
            if ad_set.get("is_active"):
                await self.db_client.update(
                    "ad_sets",
                    data={"is_active": False, "status": "archived"},
                    filters={"id": ad_set["id"]}
                )
        
        logger.info(f"✔ Deactivated {len(campaigns)} campaigns and {len(ad_sets)} ad sets")
    
    async def save_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Save validated campaign plan to database and return saved records"""
        logger.info("Saving new campaign plan...")
        
        saved_campaigns = []
        
        for campaign_data in plan.get("campaigns", []):
            # Generate proper UUID for campaign
            campaign_id = str(uuid.uuid4())
            
            # Extract budget and schedule properly
            budget = campaign_data.get("budget", {})
            schedule = campaign_data.get("schedule", {})
            
            # Save campaign
            campaign_entry = {
                "id": campaign_id,
                "initiative_id": self.config.initiative_id,
                "name": campaign_data.get("name"),
                "objective": campaign_data.get("objective"),
                "description": campaign_data.get("description"),
                "status": "active",
                "is_active": True,
                "lifetime_budget": budget.get("lifetime") if isinstance(budget, dict) else None,
                "start_date": schedule.get("start_date") if isinstance(schedule, dict) else None,
                "end_date": schedule.get("end_date") if isinstance(schedule, dict) else None,
                "execution_id": self.execution_id
            }
            
            saved_campaign = await self.db_client.insert("campaigns", campaign_entry)
            
            # Build the campaign structure for Content Creator
            campaign_with_ad_sets = {
                "id": saved_campaign["id"],
                "name": saved_campaign["name"],
                "objective": saved_campaign["objective"],
                "ad_sets": []
            }
            
            # Save ad sets for this campaign
            for ad_set_data in campaign_data.get("ad_sets", []):
                ad_set_id = str(uuid.uuid4())
                
                # Extract nested data properly
                target_audience = ad_set_data.get("target_audience", {})
                creative_brief = ad_set_data.get("creative_brief", {})
                materials = ad_set_data.get("materials", {})
                ad_set_budget = ad_set_data.get("budget", {})
                
                ad_set_entry = {
                    "id": ad_set_id,
                    "campaign_id": campaign_id,
                    "initiative_id": self.config.initiative_id,
                    "name": ad_set_data.get("name"),
                    "status": "active",
                    "is_active": True,
                    "target_audience": target_audience.dict() if hasattr(target_audience, 'dict') else target_audience,
                    "creative_brief": creative_brief.dict() if hasattr(creative_brief, 'dict') else creative_brief,
                    "materials": materials.dict() if hasattr(materials, 'dict') else materials,
                    "post_frequency": ad_set_data.get("post_frequency", 3),
                    "post_volume": ad_set_data.get("post_volume", 5),
                    "daily_budget": ad_set_budget.get("daily") if isinstance(ad_set_budget, dict) else None,
                    "lifetime_budget": ad_set_budget.get("lifetime") if isinstance(ad_set_budget, dict) else None,
                    "execution_id": self.execution_id
                }
                
                saved_ad_set = await self.db_client.insert("ad_sets", ad_set_entry)
                
                # Add to campaign structure
                campaign_with_ad_sets["ad_sets"].append({
                    "id": saved_ad_set["id"],
                    "name": saved_ad_set["name"],
                    "creative_brief": saved_ad_set.get("creative_brief", {}),
                    "materials": saved_ad_set.get("materials", {}),
                    "target_audience": saved_ad_set.get("target_audience", {}),
                    "post_frequency": saved_ad_set.get("post_frequency", 3),
                    "post_volume": saved_ad_set.get("post_volume", 5)
                })
            
            saved_campaigns.append(campaign_with_ad_sets)
        
        logger.info(f"✅ CAMPAIGN PLAN SAVED: {len(saved_campaigns)} campaigns")
        return saved_campaigns
    
    def _ensure_valid_uuid(self, id_value: str) -> str:
        """Ensure valid UUID format"""
        try:
            return str(UUID(id_value))
        except:
            return str(uuid.uuid4())