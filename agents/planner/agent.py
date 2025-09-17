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
        """Delegate to prompt builder"""
        return self.prompt_builder.build_user_prompt(input_data, error_feedback)
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planning workflow with guardrails"""
        logger.info("\n" + "=" * 70)
        logger.info("PLANNING AGENT STARTING (WITH GUARDRAILS)")
        logger.info("=" * 70)
        
        # CRITICAL: Deactivate existing campaigns first
        await self.deactivate_existing_campaigns_and_ad_sets()
        
        # Load fresh context after deactivation
        context = await self.initiative_loader.load_full_context(force_refresh=True)
        
        # Extract research results if available
        research_results = input_data.get("research_results", {})
        
        # Build research resources
        research_resources = {
            "validated_links": research_results.get("sources", []),
            "validated_hashtags": research_results.get("recommended_hashtags", []),
            "opportunities": research_results.get("content_opportunities", [])
        }
        
        # Extract budget
        initiative = context.get("initiative", {})
        budget = {
            "daily": initiative.get("daily_budget", {}).get("amount", settings.DEFAULT_DAILY_BUDGET),
            "total": initiative.get("total_budget", {}).get("amount", settings.DEFAULT_CAMPAIGN_BUDGET)
        }
        
        # Prepare structured input
        planning_input = {
            "context": context,
            "research_resources": research_resources,
            "budget": budget,
            "initiative": initiative
        }
        
        # Use BaseAgent's retry logic with structured output
        result = await self.execute_with_retries(planning_input)
        
        # Validate with guardrails
        is_valid, error_msg = self.validator.validate(result, context)
        if not is_valid:
            raise ValueError(f"Guardrail validation failed: {error_msg}")
        
        # Save validated plan
        await self.save_plan(result)
        
        logger.info("✅ Planning completed with guardrail validation")
        return result
    
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
    
    async def save_plan(self, plan: Dict[str, Any]):
        """Save validated campaign plan to database"""
        logger.info("Saving new campaign plan...")
        
        for campaign_data in plan.get("campaigns", []):
            # Ensure valid UUID
            campaign_id = self._ensure_valid_uuid(campaign_data.get("id"))
            
            # Save campaign
            campaign_entry = {
                "id": campaign_id,
                "initiative_id": self.config.initiative_id,
                "name": campaign_data.get("name"),
                "objective": campaign_data.get("objective"),
                "status": "active",
                "is_active": True,
                "execution_id": self.execution_id
            }
            
            saved_campaign = await self.db_client.insert("campaigns", campaign_entry)
            
            # Save ad sets
            for ad_set_data in campaign_data.get("ad_sets", []):
                ad_set_id = self._ensure_valid_uuid(ad_set_data.get("id"))
                
                ad_set_entry = {
                    "id": ad_set_id,
                    "campaign_id": campaign_id,
                    "initiative_id": self.config.initiative_id,
                    "name": ad_set_data.get("name"),
                    "status": "active",
                    "is_active": True,
                    "execution_id": self.execution_id
                }
                
                await self.db_client.insert("ad_sets", ad_set_entry)
        
        logger.info("✔ Campaign plan saved")
    
    def _ensure_valid_uuid(self, id_value: str) -> str:
        """Ensure valid UUID format"""
        try:
            return str(UUID(id_value))
        except:
            return str(uuid.uuid4())
