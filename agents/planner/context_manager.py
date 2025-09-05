# agents/planner/context_manager.py

"""
Context management for the Planning Agent.
Handles fetching and organizing context data from research and initiatives.
"""

from typing import Dict, Any, List
from backend.db.supabase_client import DatabaseClient
import logging
import json

logger = logging.getLogger(__name__)


class PlannerContextManager:
    """Manages context gathering and organization for planning"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.db_client = DatabaseClient(initiative_id=initiative_id)
    
    async def gather_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather all necessary context for planning including research and initiative goals
        """
        logger.info("="*60)
        logger.info("GATHERING PLANNING CONTEXT")
        logger.info("="*60)
        
        # Get initiative info
        initiatives = await self.db_client.select(
            "initiatives",
            filters={"id": self.initiative_id}
        )
        initiative = initiatives[0] if initiatives else {}
        
        logger.info("\n📋 INITIATIVE INFORMATION:")
        logger.info(f"  Name: {initiative.get('name', 'Unknown')}")
        logger.info(f"  Category: {initiative.get('category', 'N/A')}")
        
        objectives = initiative.get('objectives') or {}
        logger.info(f"  Primary Objective: {objectives.get('primary', 'N/A')}")
        logger.info(f"  Optimization Metric: {initiative.get('optimization_metric', 'reach')}")
        
        daily_budget = initiative.get('daily_budget') or {}
        total_budget = initiative.get('total_budget') or {}
        logger.info(f"  Daily Budget: ${daily_budget.get('amount', 0)}")
        logger.info(f"  Total Budget: ${total_budget.get('amount', 0)}")
        
        # Get current campaigns
        campaigns = await self.db_client.select(
            "campaigns",
            filters={
                "initiative_id": self.initiative_id,
                "is_active": True
            }
        )
        
        logger.info(f"\n📊 EXISTING CAMPAIGNS: {len(campaigns)} active")
        for camp in campaigns[:3]:
            logger.info(f"  - {camp.get('name')}: {camp.get('objective')} (${camp.get('lifetime_budget', 0)})")
        
        # Get recent research - THIS IS CRITICAL FOR GROUNDING
        research = await self.db_client.select(
            "research",
            filters={"initiative_id": self.initiative_id},
            limit=10
        )
        
        logger.info(f"\n🔬 RESEARCH DATA: {len(research)} entries found")
        
        # Extract research insights
        research_links = set()
        research_hashtags = set()
        research_themes = []
        research_opportunities = []
        
        for r in research:
            sources = r.get("sources", [])
            research_links.update(sources)
            
            raw_data = r.get("raw_data", {})
            hashtags = raw_data.get("recommended_hashtags", [])
            research_hashtags.update(hashtags)
            
            insights = r.get("insights", [])
            for insight in insights[:3]:
                if isinstance(insight, dict):
                    research_themes.append(insight.get("finding", ""))
            
            opportunities = raw_data.get("content_opportunities", [])
            research_opportunities.extend(opportunities)
        
        logger.info(f"\n🔗 RESEARCH-VALIDATED RESOURCES:")
        logger.info(f"  Links found: {len(research_links)}")
        logger.info(f"  Hashtags found: {len(research_hashtags)}")
        logger.info(f"  Content opportunities: {len(research_opportunities)}")
        
        # Build comprehensive context
        context = {
            "initiative": {
                "id": self.initiative_id,
                "name": initiative.get("name", ""),
                "objectives": objectives,
                "optimization_metric": initiative.get("optimization_metric", "reach"),
                "target_metrics": initiative.get("target_metrics") or {},
                "category": initiative.get("category", ""),
                "description": initiative.get("description", ""),
                "facebook_url": initiative.get("facebook_page_url", ""),
                "instagram_url": initiative.get("instagram_url", "")
            },
            "current_campaigns": campaigns,
            "research": research,
            "research_resources": {
                "validated_links": list(research_links),
                "validated_hashtags": list(research_hashtags),
                "content_themes": research_themes,
                "opportunities": research_opportunities
            },
            "budget": {
                "daily": daily_budget.get("amount") or 100,
                "total": total_budget.get("amount") or 10000
            },
            "metrics": []
        }
        
        logger.info("\n" + "="*60)
        logger.info("CONTEXT GATHERING COMPLETE")
        logger.info("="*60)
        
        return context
    
    def create_planning_prompt(self, context: Dict[str, Any]) -> str:
        """Create the prompt for campaign planning with emphasis on research grounding"""
        validated_links = context['research_resources']['validated_links'].copy()
        if context['initiative'].get('facebook_url'):
            validated_links.append(context['initiative']['facebook_url'])
        if context['initiative'].get('instagram_url'):
            validated_links.append(context['initiative']['instagram_url'])
        
        return f"""
        Plan marketing campaigns based on the following context. 
        YOU MUST GROUND ALL DECISIONS IN THE PROVIDED RESEARCH DATA.
        
        INITIATIVE GOALS AND IDENTITY:
        Name: {context['initiative']['name']}
        Primary Objective: {context['initiative']['objectives'].get('primary', 'N/A')}
        Category: {context['initiative']['category']}
        Description: {context['initiative']['description']}
        Optimization Metric: {context['initiative']['optimization_metric']}
        
        VALIDATED RESEARCH RESOURCES (USE THESE ONLY):
        Available Links: {json.dumps(validated_links, indent=2)}
        Research-Validated Hashtags: {json.dumps(context['research_resources']['validated_hashtags'], indent=2)}
        Content Opportunities: {json.dumps(context['research_resources']['opportunities'], indent=2)}
        
        Current Active Campaigns: {len(context.get('current_campaigns', []))}
        
        Budget Information:
        - Daily Budget: ${context['budget']['daily']}
        - Total Budget: ${context['budget']['total']}
        
        Create a comprehensive campaign hierarchy that demonstrates clear connections to the research data.
        """
