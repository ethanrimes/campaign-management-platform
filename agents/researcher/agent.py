# agents/researcher/agent.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from tools.search.perplexity_search import PerplexitySearch
from tools.search.facebook_search import FacebookSearch
from tools.search.instagram_search import InstagramSearch
from backend.config.database import SupabaseClient
import json
import uuid


class ResearchAgent(BaseAgent):
    """Research agent for gathering insights and competitive intelligence"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.db_client = SupabaseClient(tenant_id=config.tenant_id)
        self.perplexity = PerplexitySearch()
        self.facebook = FacebookSearch()
        self.instagram = InstagramSearch()
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize research-specific tools"""
        return [
            self.perplexity,
            self.facebook,
            self.instagram
        ]
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for researcher"""
        with open("agents/researcher/prompts/system_prompt.txt", "r") as f:
            return f.read()
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the research agent"""
        # Get initiative context
        initiative_id = self.config.initiative_id
        context = await self._gather_context(initiative_id)
        
        # Determine research priorities
        research_plan = self._create_research_plan(context)
        
        # Execute research
        research_results = await self._execute_research(research_plan)
        
        # Synthesize insights
        insights = self._synthesize_insights(research_results, context)
        
        # Store research in database
        await self._store_research(insights)
        
        return insights
    
    async def _gather_context(self, initiative_id: str) -> Dict[str, Any]:
        """Gather context about the initiative"""
        # Get initiative details
        initiatives = await self.db_client.select(
            "initiatives",
            filters={"id": initiative_id}
        )
        initiative = initiatives[0] if initiatives else {}
        
        # Get recent research
        existing_research = await self.db_client.select(
            "research",
            filters={"initiative_id": initiative_id},
            limit=10
        )
        
        # Get current campaigns
        campaigns = await self.db_client.select(
            "campaigns",
            filters={
                "initiative_id": initiative_id,
                "is_active": True
            }
        )
        
        return {
            "initiative": initiative,
            "existing_research": existing_research,
            "current_campaigns": campaigns
        }
    
    def _create_research_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a research plan based on context"""
        initiative = context["initiative"]
        
        # Extract key topics from initiative
        category = initiative.get("category", "general")
        objectives = initiative.get("objectives", {})
        
        research_plan = {
            "topics": [],
            "competitor_pages": [],
            "hashtags": [],
            "trends": []
        }
        
        # Define research topics based on category
        if category == "Education":
            research_plan["topics"] = [
                "education technology trends",
                "online learning best practices",
                "student engagement strategies"
            ]
        elif category == "Career/Recruiting":
            research_plan["topics"] = [
                "tech recruiting trends",
                "software engineering job market",
                "employer branding strategies"
            ]
        
        # Add initiative-specific topics
        if "primary" in objectives:
            research_plan["topics"].append(objectives["primary"])
        
        return research_plan
    
    async def _execute_research(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the research plan"""
        results = {
            "web_research": [],
            "social_research": [],
            "hashtag_research": [],
            "competitor_analysis": []
        }
        
        # Web research via Perplexity
        for topic in plan["topics"]:
            try:
                search_results = await self.perplexity.search(
                    query=topic,
                    max_results=5,
                    search_type="general"
                )
                results["web_research"].append({
                    "topic": topic,
                    "results": search_results
                })
            except Exception as e:
                print(f"Error searching for {topic}: {e}")
        
        # Social media research
        for topic in plan["topics"][:3]:  # Limit to avoid rate limits
            # Facebook pages
            fb_pages = await self.facebook.search_pages(
                query=topic,
                limit=5
            )
            results["social_research"].append({
                "platform": "facebook",
                "topic": topic,
                "pages": fb_pages
            })
            
            # Instagram hashtags
            hashtags = await self.instagram.search_hashtags(
                query=topic,
                limit=20
            )
            results["hashtag_research"].append({
                "topic": topic,
                "hashtags": hashtags
            })
        
        return results
    
    def _synthesize_insights(self, research: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize research into actionable insights"""
        insights = {
            "summary": "",
            "key_findings": [],
            "content_opportunities": [],
            "recommended_hashtags": [],
            "competitor_insights": [],
            "trending_topics": [],
            "sources": []
        }
        
        # Process web research
        for web_result in research.get("web_research", []):
            topic = web_result["topic"]
            for result in web_result["results"]:
                insights["key_findings"].append({
                    "topic": topic,
                    "finding": result.get("snippet", ""),
                    "source": result.get("url", ""),
                    "relevance": result.get("relevance_score", 0.5)
                })
                insights["sources"].append(result.get("url", ""))
        
        # Process hashtag research
        all_hashtags = set()
        for hashtag_result in research.get("hashtag_research", []):
            all_hashtags.update(hashtag_result["hashtags"])
        insights["recommended_hashtags"] = list(all_hashtags)[:30]
        
        # Process social research
        for social_result in research.get("social_research", []):
            if social_result["platform"] == "facebook":
                for page in social_result["pages"]:
                    insights["competitor_insights"].append({
                        "name": page["name"],
                        "category": page.get("category", ""),
                        "link": page["link"],
                        "followers": page.get("fan_count", 0)
                    })
        
        # Create summary
        insights["summary"] = self._generate_summary(insights, context)
        
        return insights
    
    def _generate_summary(self, insights: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate a summary of the research findings"""
        initiative_name = context["initiative"].get("name", "the initiative")
        num_findings = len(insights["key_findings"])
        num_competitors = len(insights["competitor_insights"])
        
        summary = f"Research completed for {initiative_name}. "
        summary += f"Analyzed {num_findings} key findings across multiple topics. "
        summary += f"Identified {num_competitors} relevant competitor pages and "
        summary += f"{len(insights['recommended_hashtags'])} trending hashtags. "
        
        if insights["key_findings"]:
            top_finding = insights["key_findings"][0]
            summary += f"Key insight: {top_finding['finding'][:100]}..."
        
        return summary
    
    async def _store_research(self, insights: Dict[str, Any]):
        """Store research results in database"""
        research_entry = {
            "tenant_id": self.config.tenant_id,
            "initiative_id": self.config.initiative_id,
            "research_type": "comprehensive",
            "topic": "scheduled_research",
            "summary": insights["summary"],
            "insights": insights["key_findings"],
            "raw_data": insights,
            "sources": insights["sources"],
            "relevance_score": {"overall": 0.8},
            "tags": ["automated", "scheduled"],
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        await self.db_client.insert("research", research_entry)
    
    def validate_output(self, output: Any) -> bool:
        """Validate research output"""
        if not isinstance(output, dict):
            return False
        
        required_fields = ["summary", "key_findings", "recommended_hashtags"]
        if not all(field in output for field in required_fields):
            return False
        
        return True