# agents/orchestrator/agent.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from agents.orchestrator.models import (
    OrchestratorOutput, Campaign, AdSet, BudgetAllocation,
    Schedule, TargetAudience, CreativeBrief, Materials,
    OptimizationStrategy, CampaignObjective
)
from backend.config.database import SupabaseClient
import uuid
import json


class OrchestratorAgent(BaseAgent):
    """Main orchestrator agent for campaign management with structured output"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.db_client = SupabaseClient(tenant_id=config.tenant_id)
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize orchestrator-specific tools"""
        return []  # Tools will be called via methods
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for orchestrator with structured output instructions"""
        base_prompt = ""
        with open("agents/orchestrator/prompts/system_prompt.txt", "r") as f:
            base_prompt = f.read()
        
        # Add structured output schema information
        schema_prompt = """
        
        You must return your response as a valid JSON object that conforms to this exact schema:
        {
            "campaigns": [
                {
                    "id": "unique-id",
                    "name": "Campaign Name",
                    "objective": "AWARENESS|ENGAGEMENT|TRAFFIC|CONVERSIONS",
                    "description": "Optional description",
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
                                "locations": ["location1", "location2"],
                                "interests": ["interest1", "interest2"],
                                "languages": ["English"]
                            },
                            "placements": ["ig_feed", "fb_feed"],
                            "budget": {
                                "daily": 50.0,
                                "lifetime": 1500.0
                            },
                            "creative_brief": {
                                "theme": "Content theme",
                                "tone": "professional|casual|friendly",
                                "format_preferences": ["image", "video"],
                                "key_messages": ["message1", "message2"]
                            },
                            "materials": {
                                "links": ["url1", "url2"],
                                "hashtags": ["#tag1", "#tag2"],
                                "brand_assets": ["asset1"]
                            },
                            "post_frequency": 3,
                            "post_volume": 5
                        }
                    ]
                }
            ],
            "total_budget_allocated": 3000.0,
            "optimization_strategy": {
                "primary_metric": "reach|engagement|conversions",
                "secondary_metrics": ["metric1", "metric2"],
                "allocation_method": "balanced|aggressive|conservative",
                "reasoning": "Explanation of strategy"
            },
            "revision_notes": "Optional notes about changes",
            "recommendations": ["recommendation1", "recommendation2"]
        }
        
        Ensure all dates are in ISO format, all budgets are positive numbers, and all required fields are present.
        """
        
        return base_prompt + schema_prompt
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the orchestrator agent with structured output"""
        # Gather context
        context = await self._gather_context(input_data)
        
        # Prepare prompt with all context
        prompt = self._create_planning_prompt(context)
        
        # Get model config
        from backend.config.settings import settings
        model_config = self.config.model_config or self._load_model_config()
        
        # Call OpenAI API for campaign planning
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
        
        # Convert to Pydantic models for validation
        orchestrator_output = self._parse_to_pydantic(raw_output, context)
        
        # Validate budget allocation
        orchestrator_output = self._validate_and_adjust_budget(
            orchestrator_output, 
            context["budget"]["total"]
        )
        
        # Convert back to dict for storage
        return orchestrator_output.dict()
    
    def _parse_to_pydantic(self, raw_output: Dict[str, Any], context: Dict[str, Any]) -> OrchestratorOutput:
        """Parse raw output into Pydantic models with validation"""
        # Parse campaigns
        campaigns = []
        for camp_data in raw_output.get("campaigns", []):
            # Parse ad sets
            ad_sets = []
            for ad_set_data in camp_data.get("ad_sets", []):
                ad_set = AdSet(
                    id=ad_set_data.get("id", str(uuid.uuid4())),
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
            
            # Parse campaign
            campaign = Campaign(
                id=camp_data.get("id", str(uuid.uuid4())),
                name=camp_data["name"],
                objective=CampaignObjective(camp_data["objective"]),
                description=camp_data.get("description"),
                budget=BudgetAllocation(**camp_data.get("budget", {})),
                schedule=Schedule(
                    start_date=datetime.fromisoformat(camp_data["schedule"]["start_date"]),
                    end_date=datetime.fromisoformat(camp_data["schedule"]["end_date"])
                ),
                ad_sets=ad_sets
            )
            campaigns.append(campaign)
        
        # Create optimization strategy
        opt_strategy = OptimizationStrategy(
            primary_metric=raw_output.get("optimization_strategy", {}).get("primary_metric", "reach"),
            secondary_metrics=raw_output.get("optimization_strategy", {}).get("secondary_metrics", []),
            allocation_method=raw_output.get("optimization_strategy", {}).get("allocation_method", "balanced"),
            reasoning=raw_output.get("optimization_strategy", {}).get("reasoning", "Default strategy")
        )
        
        # Create orchestrator output
        output = OrchestratorOutput(
            campaigns=campaigns,
            total_budget_allocated=raw_output.get("total_budget_allocated", 0),
            optimization_strategy=opt_strategy,
            revision_notes=raw_output.get("revision_notes"),
            recommendations=raw_output.get("recommendations", [])
        )
        
        return output
    
    def _validate_and_adjust_budget(self, output: OrchestratorOutput, total_budget: float) -> OrchestratorOutput:
        """Validate and adjust budget allocation if needed"""
        # Calculate actual total from campaigns
        actual_total = sum(
            campaign.budget.lifetime or 0 
            for campaign in output.campaigns
        )
        
        # If over budget, scale down proportionally
        if actual_total > total_budget:
            scale_factor = total_budget / actual_total
            
            for campaign in output.campaigns:
                if campaign.budget.lifetime:
                    campaign.budget.lifetime *= scale_factor
                if campaign.budget.daily:
                    campaign.budget.daily *= scale_factor
                
                # Also scale ad set budgets
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
    
    async def _gather_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gather all necessary context for planning"""
        initiative_id = self.config.initiative_id
        
        # Get initiative info
        initiatives = await self.db_client.select(
            "initiatives",
            filters={"id": initiative_id}
        )
        initiative = initiatives[0] if initiatives else {}
        
        # Get current campaigns
        campaigns = await self.db_client.select(
            "campaigns",
            filters={
                "initiative_id": initiative_id,
                "is_active": True
            }
        )
        
        # Get recent research
        research = await self.db_client.select(
            "research",
            filters={"initiative_id": initiative_id},
            limit=5
        )
        
        # Get metrics
        metrics = await self.db_client.select(
            "metrics",
            filters={"entity_type": "campaign"},
            limit=10
        )
        
        return {
            "initiative": {
                "name": initiative.get("name", ""),
                "objectives": initiative.get("objectives", {}),
                "optimization_metric": initiative.get("optimization_metric", "reach"),
                "target_metrics": initiative.get("target_metrics", {})
            },
            "current_campaigns": campaigns,
            "research": research,
            "budget": {
                "daily": initiative.get("daily_budget", {}).get("amount", 100),
                "total": initiative.get("total_budget", {}).get("amount", 10000)
            },
            "metrics": metrics
        }
    
    def _create_planning_prompt(self, context: Dict[str, Any]) -> str:
        """Create the prompt for campaign planning"""
        return f"""
        Plan marketing campaigns based on the following context:
        
        Initiative Information:
        {json.dumps(context['initiative'], indent=2)}
        
        Current Active Campaigns:
        {json.dumps(context.get('current_campaigns', []), indent=2)}
        
        Recent Research Insights:
        {json.dumps(context.get('research', []), indent=2)}
        
        Budget Information:
        - Daily Budget: ${context['budget']['daily']}
        - Total Budget: ${context['budget']['total']}
        
        Current Performance Metrics:
        {json.dumps(context.get('metrics', []), indent=2)}
        
        Please create a comprehensive campaign hierarchy that:
        1. Aligns with the initiative objectives
        2. Stays within budget constraints
        3. Leverages research insights
        4. Optimizes for {context['initiative'].get('optimization_metric', 'reach')}
        
        Ensure each campaign has clear objectives and each ad set has specific targeting and creative briefs.
        """
    
    def validate_output(self, output: Any) -> bool:
        """Validate orchestrator output using Pydantic"""
        if not isinstance(output, dict):
            return False
        
        try:
            # Try to parse as OrchestratorOutput
            OrchestratorOutput(**output)
            return True
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    async def save_hierarchy(self, hierarchy: Dict[str, Any]):
        """Save the campaign hierarchy to database"""
        for campaign_data in hierarchy["campaigns"]:
            # Save campaign
            campaign_entry = {
                "id": campaign_data["id"],
                "tenant_id": self.config.tenant_id,
                "initiative_id": self.config.initiative_id,
                "name": campaign_data["name"],
                "objective": campaign_data["objective"],
                "daily_budget": campaign_data.get("budget", {}).get("daily"),
                "lifetime_budget": campaign_data.get("budget", {}).get("lifetime"),
                "start_date": campaign_data.get("schedule", {}).get("start_date"),
                "end_date": campaign_data.get("schedule", {}).get("end_date"),
                "status": "draft",
                "is_active": True
            }
            
            await self.db_client.insert("campaigns", campaign_entry)
            
            # Save ad sets
            for ad_set_data in campaign_data.get("ad_sets", []):
                ad_set_entry = {
                    "id": ad_set_data["id"],
                    "tenant_id": self.config.tenant_id,
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
                    "is_active": True
                }
                
                await self.db_client.insert("ad_sets", ad_set_entry)