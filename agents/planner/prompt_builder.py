# agents/planner/prompt_builder.py

from typing import Dict, Any, Optional
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class PlannerPromptBuilder:
    """Builds dynamic prompts for planner agent"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.base_prompt_path = "agents/planner/prompts/system_prompt.txt"
    
    def get_system_prompt(self) -> str:
        """Build complete system prompt with planning rules"""
        base_prompt = self._load_base_prompt()
        
        limits = f"""

PLANNING LIMITS AND CONSTRAINTS:
================================

WORKFLOW BEHAVIOR:
- When called, ALL existing campaigns/ad_sets are automatically deactivated
- You are creating the COMPLETE active campaign strategy
- Previous campaigns are archived before your planning begins
- Your output represents the ENTIRE active campaign structure

CAMPAIGN LIMITS:
- Minimum active campaigns: {settings.MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE}
- Maximum active campaigns: {settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE}
- You MUST create campaigns within this range

AD SET LIMITS PER CAMPAIGN:
- Minimum ad sets per campaign: {settings.MIN_ACTIVE_AD_SETS_PER_CAMPAIGN}
- Maximum ad sets per campaign: {settings.MAX_ACTIVE_AD_SETS_PER_CAMPAIGN}

CONTENT LIMITS (for reference):
- Max Facebook posts per ad set: {settings.MAX_FACEBOOK_POSTS_PER_AD_SET}
- Max Instagram posts per ad set: {settings.MAX_INSTAGRAM_POSTS_PER_AD_SET}
- Max photos per ad set: {settings.MAX_PHOTOS_PER_AD_SET}
- Max videos per ad set: {settings.MAX_VIDEOS_PER_AD_SET}

OUTPUT STRUCTURE REQUIREMENTS:
- Must provide PlannerOutput with all required fields
- campaigns: List of AgentCampaign objects
- total_budget_allocated: Total budget across all campaigns
- optimization_strategy: Clear strategy with metrics and reasoning
- Each campaign must have valid UUID for id field
- Each ad set must have valid UUID for id field

CRITICAL RULES:
1. Create a COMPLETE campaign strategy (not additions)
2. Use FULL available budget (not partial allocations)
3. Use ONLY validated links and hashtags from research
4. ALL decisions must be grounded in research data
"""
        
        return base_prompt + limits
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build user prompt with planning context"""
        context = input_data.get("context", {})
        research_resources = input_data.get("research_resources", {})
        budget = input_data.get("budget", {})
        initiative = input_data.get("initiative", context.get("initiative", {}))
        
        # Extract statistics
        stats = context.get("statistics", {})
        
        prompt = f"""
Create a COMPLETE marketing campaign strategy. All previous campaigns have been archived.
You are creating the ENTIRE active campaign structure for this initiative.

INITIATIVE CONTEXT:
==================
Name: {initiative.get('name', 'Unknown')}
Category: {initiative.get('category', 'N/A')}
Description: {initiative.get('description', 'N/A')}
Objectives: {self._format_objectives(initiative.get('objectives', {}))}
Optimization Metric: {initiative.get('optimization_metric', 'reach')}

AVAILABLE BUDGET (USE FULLY):
=============================
Daily Budget: ${budget.get('daily', 100)}
Total Budget: ${budget.get('total', 10000)}

RESEARCH-VALIDATED RESOURCES:
=============================
Validated Links ({len(research_resources.get('validated_links', []))} available):
{self._format_links(research_resources.get('validated_links', []))}

Validated Hashtags ({len(research_resources.get('validated_hashtags', []))} available):
{self._format_hashtags(research_resources.get('validated_hashtags', []))}

Content Opportunities:
{self._format_opportunities(research_resources.get('opportunities', []))}

HISTORICAL CONTEXT (now archived):
==================================
- Previously had {stats.get('total_campaigns', 0)} campaigns (now archived)
- Previously had {stats.get('total_ad_sets', 0)} ad sets (now archived)
- Generated {stats.get('total_posts', 0)} posts historically

REQUIREMENTS FOR YOUR OUTPUT:
=============================
1. Create {settings.MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE} to {settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE} campaigns
2. Each campaign needs {settings.MIN_ACTIVE_AD_SETS_PER_CAMPAIGN}-{settings.MAX_ACTIVE_AD_SETS_PER_CAMPAIGN} ad sets
3. Allocate the FULL available budget (not partial)
4. Use ONLY validated links and hashtags from research
5. Ground ALL decisions in research data
6. Include complete targeting, creative briefs, and materials
7. Provide clear optimization strategy

Create a comprehensive PlannerOutput that becomes the complete active strategy.
"""
        
        if error_feedback:
            prompt += f"""

IMPORTANT - PREVIOUS ATTEMPT FAILED:
====================================
{error_feedback}

Please correct this issue and ensure all required fields are properly formatted.
"""
        
        return prompt
    
    def _load_base_prompt(self) -> str:
        """Load base system prompt from file"""
        try:
            with open(self.base_prompt_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load base prompt: {e}")
            return """You are an expert marketing campaign planner AI responsible for creating 
strategic campaign hierarchies grounded in research data."""
    
    def _format_objectives(self, objectives: Dict[str, Any]) -> str:
        """Format objectives"""
        if not objectives:
            return "None specified"
        
        lines = []
        for key, value in objectives.items():
            lines.append(f"  - {key}: {value}")
        return "\n".join(lines)
    
    def _format_links(self, links: list) -> str:
        """Format validated links"""
        if not links:
            return "  No validated links available"
        
        return "\n".join(f"  - {link}" for link in links[:10])
    
    def _format_hashtags(self, hashtags: list) -> str:
        """Format validated hashtags"""
        if not hashtags:
            return "  No validated hashtags available"
        
        # Handle both dict and string formats
        formatted = []
        for h in hashtags[:20]:
            if isinstance(h, dict):
                formatted.append(f"  - {h.get('hashtag', h)}")
            else:
                formatted.append(f"  - {h}")
        
        return "\n".join(formatted)
    
    def _format_opportunities(self, opportunities: list) -> str:
        """Format content opportunities"""
        if not opportunities:
            return "  No specific opportunities identified"
        
        formatted = []
        for opp in opportunities[:5]:
            if isinstance(opp, dict):
                formatted.append(f"  - {opp.get('description', opp)}")
            else:
                formatted.append(f"  - {opp}")
        
        return "\n".join(formatted)
