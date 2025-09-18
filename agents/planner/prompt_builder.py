# agents/planner/prompt_builder.py

from typing import Dict, Any, Optional
from backend.config.settings import settings
import json
import logging
from datetime import datetime, timedelta

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
        """Build user prompt with planning context - with escaped braces"""
        context = input_data.get("context", {})
        research_resources = input_data.get("research_resources", {})
        budget = input_data.get("budget", {})
        initiative = input_data.get("initiative", context.get("initiative", {}))
        
        # Extract statistics
        stats = context.get("statistics", {})
        
        # Format objectives - escape any braces in the output
        objectives_str = self._format_objectives(initiative.get('objectives', {}))
        
        # Format links and hashtags - ensure no unescaped braces
        links_str = self._format_links(research_resources.get('validated_links', []))
        hashtags_str = self._format_hashtags(research_resources.get('validated_hashtags', []))
        opportunities_str = self._format_opportunities(research_resources.get('opportunities', []))

        # Get current date for context
        current_date = datetime.now()
        date_str = current_date.strftime("%Y-%m-%d")
        suggested_start = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        suggested_end = (current_date + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        
        prompt = f"""
Create a COMPLETE marketing campaign strategy. All previous campaigns have been archived.
You are creating the ENTIRE active campaign structure for this initiative.

CURRENT DATE CONTEXT:
====================
Today's Date: {date_str}
Current DateTime: {current_date.isoformat()}Z

IMPORTANT: All campaigns must have dates in the FUTURE from today ({date_str}).
Example valid schedule:
  start_date: "{suggested_start}"
  end_date: "{suggested_end}"

INITIATIVE CONTEXT:
==================
Name: {initiative.get('name', 'Unknown')}
Category: {initiative.get('category', 'N/A')}
Description: {initiative.get('description', 'N/A')}
Objectives: {objectives_str}
Optimization Metric: {initiative.get('optimization_metric', 'reach')}

AVAILABLE BUDGET (USE FULLY):
=============================
Daily Budget: ${budget.get('daily', 100)}
Total Budget: ${budget.get('total', 10000)}

RESEARCH-VALIDATED RESOURCES:
=============================
Validated Links ({len(research_resources.get('validated_links', []))} available):
{links_str}

Validated Hashtags ({len(research_resources.get('validated_hashtags', []))} available):
{hashtags_str}

Content Opportunities:
{opportunities_str}

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
            # Parse the error to provide specific guidance
            if "past" in error_feedback.lower() or "already ended" in error_feedback.lower():
                error_guidance = """
    CRITICAL ERROR - DATES IN THE PAST:
    Your previous attempt used dates that have already passed.
    ALL campaigns must have FUTURE dates starting from today ({date_str}) or later.
    DO NOT use dates from 2023 or any past dates!
    """
            elif "campaign limit" in error_feedback.lower():
                error_guidance = """
    CRITICAL ERROR - CAMPAIGN COUNT:
    You must create between {settings.MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE} and {settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE} campaigns.
    Your previous attempt did not meet these requirements.
    """
            else:
                error_guidance = error_feedback
                
            prompt += f"""

    ⚠️ PREVIOUS ATTEMPT FAILED - MUST FIX:
    =====================================
    {error_guidance}

    Original error: {error_feedback}

    Please correct these issues in your new attempt.
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
        """Format objectives - safely handling any dict structures"""
        if not objectives:
            return "None specified"
        
        lines = []
        for key, value in objectives.items():
            # Convert value to string and escape braces if it's a dict/list representation
            value_str = str(value)
            if '{' in value_str or '}' in value_str:
                value_str = value_str.replace('{', '{{').replace('}', '}}')
            lines.append(f"  - {key}: {value_str}")
        return "\n".join(lines)
    
    def _format_links(self, links: list) -> str:
        """Format validated links - safely"""
        if not links:
            return "  No validated links available"
        
        formatted = []
        for link in links[:10]:
            if isinstance(link, dict):
                # If it's a dict, extract URL safely
                url = link.get('url', str(link))
                # Escape any braces in the URL
                safe_url = url.replace('{', '{{').replace('}', '}}')
                formatted.append(f"  - {safe_url}")
            else:
                # It's a string URL
                safe_link = str(link).replace('{', '{{').replace('}', '}}')
                formatted.append(f"  - {safe_link}")
        
        return "\n".join(formatted)
    
    def _format_hashtags(self, hashtags: list) -> str:
        """Format validated hashtags - safely"""
        if not hashtags:
            return "  No validated hashtags available"
        
        formatted = []
        for h in hashtags[:20]:
            if isinstance(h, dict):
                hashtag = h.get('hashtag', str(h))
            else:
                hashtag = str(h)
            
            # Escape any braces (unlikely in hashtags, but safe)
            safe_hashtag = hashtag.replace('{', '{{').replace('}', '}}')
            formatted.append(f"  - {safe_hashtag}")
        
        return "\n".join(formatted)
    
    def _format_opportunities(self, opportunities: list) -> str:
        """Format content opportunities - safely"""
        if not opportunities:
            return "  No specific opportunities identified"
        
        formatted = []
        for opp in opportunities[:5]:
            if isinstance(opp, dict):
                desc = opp.get('description', str(opp))
            else:
                desc = str(opp)
            
            # Escape any braces in the description
            safe_desc = desc.replace('{', '{{').replace('}', '}}')
            formatted.append(f"  - {safe_desc}")
        
        return "\n".join(formatted)