# ============================================================================
# agents/researcher/prompt_builder.py
# ============================================================================

from typing import Dict, Any, Optional, List
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ResearcherPromptBuilder:
    """Builds dynamic prompts for researcher agent"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.base_prompt_path = "agents/researcher/prompts/system_prompt.txt"
    
    def get_system_prompt(self) -> str:
        """Build complete system prompt with constraints"""
        base_prompt = self._load_base_prompt()
        
        constraints = f"""

RESEARCH CONSTRAINTS AND REQUIREMENTS:
======================================
- Maximum output length: {settings.MAX_RESEARCH_OUTPUT_LENGTH} characters
- Maximum hashtags to recommend: {settings.MAX_HASHTAGS}
- Maximum search queries: {settings.MAX_RESEARCH_QUERIES}

OUTPUT STRUCTURE REQUIREMENTS:
- Must provide ResearchOutput with all required fields
- research_type: One of [competitor, trend, hashtag, audience, comprehensive]
- summary: Must include executive_summary, key_takeaways, action_items
- key_findings: At least 5 findings with sources and relevance scores
- sources: All sources must have valid URLs
- recommended_hashtags: Maximum {settings.MAX_HASHTAGS} hashtags

QUALITY REQUIREMENTS:
- Focus on actionable, recent insights (last 3-6 months preferred)
- Validate all URLs before including
- Rate relevance of each insight (0.0-1.0)
- Prioritize quality over quantity
- Identify specific opportunities for content and engagement
"""
        
        return base_prompt + constraints
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build user prompt with research context"""
        # Extract data from input
        initiative_data = input_data.get("initiative_data", {})
        search_results = input_data.get("search_results", [])
        search_queries = input_data.get("search_queries", [])
        context = input_data.get("context", {})
        
        initiative = initiative_data.get("initiative", {})
        campaigns = initiative_data.get("campaigns", [])
        existing_research = initiative_data.get("existing_research", [])
        
        prompt = f"""
Conduct comprehensive research based on the following data:

INITIATIVE INFORMATION:
======================
Name: {initiative.get('name', 'Unknown')}
Description: {initiative.get('description', 'N/A')}
Category: {initiative.get('category', 'N/A')}
Objectives: {self._format_objectives(initiative.get('objectives', {}))}

ACTIVE CAMPAIGNS ({len(campaigns)}):
====================================
{self._format_campaigns(campaigns)}

SEARCH QUERIES EXECUTED:
========================
{chr(10).join(f"- {q}" for q in search_queries)}

SEARCH RESULTS COLLECTED ({len(search_results)} total):
========================================================
{self._format_search_results(search_results)}

EXISTING RESEARCH CONTEXT ({len(existing_research)} entries):
=============================================================
{self._format_existing_research(existing_research)}

REQUIREMENTS FOR YOUR OUTPUT:
=============================
1. Research Type: Choose the most appropriate type (comprehensive recommended)
2. Executive Summary: Clear overview of all findings
3. Key Findings: At least 5 specific, actionable findings with sources
4. Content Opportunities: Specific opportunities based on research
5. Hashtag Recommendations: Up to {settings.MAX_HASHTAGS} relevant hashtags
6. Competitor Insights: If competitors found in research
7. Trending Topics: Current trends relevant to the initiative
8. All sources must be from the search results provided

Synthesize all information into a cohesive ResearchOutput that will guide campaign planning.
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
            return """You are an expert research analyst AI specializing in social media marketing intelligence. 
Your role is to gather, analyze, and synthesize information to provide actionable insights."""
    
    def _format_objectives(self, objectives: Dict[str, Any]) -> str:
        """Format objectives for prompt"""
        if not objectives:
            return "None specified"
        
        lines = []
        for key, value in objectives.items():
            lines.append(f"  - {key}: {value}")
        return "\n".join(lines)
    
    def _format_campaigns(self, campaigns: List[Dict[str, Any]]) -> str:
        """Format campaigns for prompt"""
        if not campaigns:
            return "No active campaigns"
        
        formatted = []
        for camp in campaigns[:3]:
            formatted.append(
                f"- {camp.get('name', 'Unknown')}: "
                f"{camp.get('objective', 'N/A')} "
                f"(Budget: ${camp.get('lifetime_budget', 0)})"
            )
        
        if len(campaigns) > 3:
            formatted.append(f"- ... and {len(campaigns) - 3} more")
        
        return "\n".join(formatted)
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results summary"""
        if not results:
            return "No search results available"
        
        # Group by query
        by_query = {}
        for result in results:
            query = result.get("query", "Unknown")
            if query not in by_query:
                by_query[query] = []
            by_query[query].append(result)
        
        lines = []
        for query, query_results in list(by_query.items())[:5]:
            lines.append(f"\nQuery: '{query}' ({len(query_results)} results)")
            for r in query_results[:2]:
                lines.append(f"  - {r.get('title', 'Untitled')}: {r.get('url', '')}")
        
        return "\n".join(lines)
    
    def _format_existing_research(self, research: List[Dict[str, Any]]) -> str:
        """Format existing research summary"""
        if not research:
            return "No previous research"
        
        lines = []
        for r in research[:2]:
            lines.append(
                f"- Type: {r.get('research_type', 'Unknown')}, "
                f"Topic: {r.get('topic', 'N/A')}"
            )
        
        return "\n".join(lines)