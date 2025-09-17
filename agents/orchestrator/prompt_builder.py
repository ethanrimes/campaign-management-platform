# ============================================================================
# agents/orchestrator/prompt_builder.py
# ============================================================================

from typing import Dict, Any
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class OrchestratorPromptBuilder:
    """Builds prompts for orchestrator agent"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
    
    def get_system_prompt(self, workflow_type: str) -> str:
        """Build system prompt for orchestrator"""
        
        workflow_descriptions = {
            "full-campaign": "Execute complete campaign creation from research to content",
            "research-only": "Conduct research and analysis only",
            "planning-only": "Create campaign plans without content",
            "content-creation-only": "Generate content for existing campaigns",
            "research-then-planning": "Research followed by campaign planning",
            "planning-then-content": "Planning followed by content creation"
        }
        
        description = workflow_descriptions.get(workflow_type, "Execute workflow")
        
        return f"""You are an orchestrator AI that coordinates the execution of multiple specialized agents
to complete complex workflows. You enforce strict limits and guardrails to prevent excessive
resource usage and ensure system stability.

CURRENT WORKFLOW: {workflow_type}
DESCRIPTION: {description}

ENFORCEMENT RULES:
=================
- Maximum active campaigns: {settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE}
- Maximum ad sets per campaign: {settings.MAX_ACTIVE_AD_SETS_PER_CAMPAIGN}
- Maximum content per ad set: 
  - Facebook posts: {settings.MAX_FACEBOOK_POSTS_PER_AD_SET}
  - Instagram posts: {settings.MAX_INSTAGRAM_POSTS_PER_AD_SET}
  - Photos: {settings.MAX_PHOTOS_PER_AD_SET}
  - Videos: {settings.MAX_VIDEOS_PER_AD_SET}

You must ensure all agents respect these limits and halt execution if violations occur.
Track state across all agents and provide clear status updates.
"""
    
    def build_status_message(
        self,
        step_name: str,
        step_number: int,
        total_steps: int,
        stats: Dict[str, Any]
    ) -> str:
        """Build status message for logging"""
        
        return f"""
WORKFLOW STEP {step_number}/{total_steps}: {step_name}
========================================
Current System State:
- Active campaigns: {stats.get('active_campaigns', 0)}/{settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE}
- Total ad sets: {stats.get('total_ad_sets', 0)}
- Total posts: {stats.get('total_posts', 0)}
- Total images: {stats.get('total_images', 0)}
- Total videos: {stats.get('total_videos', 0)}
"""