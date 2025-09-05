# agents/planner/validation.py

"""
Validation utilities for the Orchestrator Agent.
Ensures outputs are grounded in research data.
"""

from typing import Dict, Any, List, Set
from agents.planner.models import PlannerOutput
import logging

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates planner outputs against research data"""
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.valid_links = set(context.get("research_resources", {}).get("validated_links", []))
        self.valid_hashtags = set(context.get("research_resources", {}).get("validated_hashtags", []))
        
        if context.get("initiative", {}).get("facebook_url"):
            self.valid_links.add(context["initiative"]["facebook_url"])
        if context.get("initiative", {}).get("instagram_url"):
            self.valid_links.add(context["initiative"]["instagram_url"])
        
        logger.info(f"\n📋 VALIDATOR INITIALIZED:")
        logger.info(f"  Valid links: {len(self.valid_links)}")
        logger.info(f"  Valid hashtags: {len(self.valid_hashtags)}")
    
    def validate_and_fix_output(self, output: PlannerOutput) -> PlannerOutput:
        """Validate and fix the planner output to ensure grounding"""
        logger.info("\n🔍 VALIDATING OUTPUT AGAINST RESEARCH DATA...")
        
        issues_found = []
        fixes_applied = []
        
        for campaign in output.campaigns:
            campaign_name = campaign.name
            
            for ad_set in campaign.ad_sets:
                ad_set_name = f"{campaign_name}/{ad_set.name}"
                
                # Validate and fix links
                original_links = ad_set.materials.links.copy() if ad_set.materials.links else []
                validated_links = self._validate_links(original_links, ad_set_name)
                
                if set(original_links) != set(validated_links):
                    issues_found.append(f"Invalid links in {ad_set_name}")
                    fixes_applied.append(f"Fixed links in {ad_set_name}")
                    ad_set.materials.links = validated_links
        
        if fixes_applied:
            logger.info(f"\n✅ FIXES APPLIED: {len(fixes_applied)}")
        else:
            logger.info("\n✅ OUTPUT VALIDATION PASSED")
        
        if output.revision_notes:
            output.revision_notes += f" Validation: {len(fixes_applied)} fixes applied."
        else:
            output.revision_notes = f"Validation: {len(fixes_applied)} fixes applied."
        
        return output
    
    def _validate_links(self, links: List[str], context_name: str) -> List[str]:
        """Validate links against research sources"""
        if not links:
            return []
        
        validated = []
        for link in links:
            if link in self.valid_links:
                validated.append(link)
            else:
                logger.warning(f"  Removed invalid link from {context_name}: {link}")
        
        return validated


class BudgetValidator:
    """Validates budget allocations"""
    
    @staticmethod
    def validate_budget_allocation(output: PlannerOutput, total_budget: float) -> tuple[bool, str]:
        """Validate that budget allocations are within limits"""
        actual_total = sum(
            campaign.budget.lifetime or 0 
            for campaign in output.campaigns
        )
        
        if actual_total > total_budget:
            return False, f"Budget exceeded: ${actual_total:.2f} > ${total_budget:.2f}"
        
        return True, f"Budget allocation valid: ${actual_total:.2f} / ${total_budget:.2f}"
