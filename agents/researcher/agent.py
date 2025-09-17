from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from agents.base.agent import BaseAgent, AgentConfig
from agents.researcher.prompt_builder import ResearcherPromptBuilder
from agents.researcher.tools.perplexity_search import PerplexitySearch
from agents.researcher.models import ResearchOutput, ResearchType
from backend.db.supabase_client import DatabaseClient
from agents.guardrails.initiative_loader import InitiativeLoader
from agents.guardrails.validators import ResearcherValidator
from backend.config.settings import settings
import json
import logging

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Research agent with structured output and guardrails"""
    
    def __init__(self, config: AgentConfig):
        self.perplexity = PerplexitySearch()
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.prompt_builder = ResearcherPromptBuilder(config.initiative_id)
        self.validator = ResearcherValidator()
        self.initiative_loader = InitiativeLoader(config.initiative_id)
        super().__init__(config)
    
    def _initialize_tools(self) -> List[Any]:
        """Initialize research tools"""
        return [self.perplexity]
    
    def get_output_model(self) -> Type[BaseModel]:
        """Return the ResearchOutput model for structured output"""
        return ResearchOutput
    
    def get_system_prompt(self) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.get_system_prompt()
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.build_user_prompt(input_data, error_feedback)
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research workflow with guardrails"""
        logger.info("=" * 60)
        logger.info("RESEARCH AGENT STARTING (WITH GUARDRAILS)")
        logger.info("=" * 60)
        
        # Load full context for guardrail validation
        context = await self.initiative_loader.load_full_context()
        
        # Gather research data
        initiative_data = await self._fetch_initiative_data()
        search_queries = self._determine_search_queries(initiative_data)
        search_results = await self._iterative_search(search_queries, initiative_data)
        
        # Prepare structured input for LangChain
        research_input = {
            "initiative_data": initiative_data,
            "search_results": search_results,
            "search_queries": search_queries,
            "context": context
        }
        
        # Use BaseAgent's retry logic with structured output
        result = await self.execute_with_retries(research_input)
        
        # Validate with guardrails
        is_valid, error_msg = self.validator.validate(result, context)
        if not is_valid:
            raise ValueError(f"Guardrail validation failed: {error_msg}")
        
        # Store validated research
        await self._store_research(result)
        
        logger.info("✅ Research completed with guardrail validation")
        return result
    
    def validate_output(self, output: Any) -> bool:
        """Validate output structure and content"""
        if not isinstance(output, dict):
            return False
        
        # Check required fields for ResearchOutput
        required_fields = ["research_type", "summary", "key_findings", "sources"]
        if not all(field in output for field in required_fields):
            return False
        
        # Additional validation via guardrails will happen in _run
        return True
    
    async def _fetch_initiative_data(self) -> Dict[str, Any]:
        """Fetch initiative and related data"""
        initiatives = await self.db_client.select(
            "initiatives",
            filters={"id": self.config.initiative_id}
        )
        
        if not initiatives:
            raise ValueError(f"Initiative not found: {self.config.initiative_id}")
        
        initiative = initiatives[0]
        
        campaigns = await self.db_client.select(
            "campaigns",
            filters={"initiative_id": self.config.initiative_id, "is_active": True},
            limit=5
        )
        
        existing_research = await self.db_client.select(
            "research",
            filters={"initiative_id": self.config.initiative_id},
            limit=3
        )
        
        return {
            "initiative": initiative,
            "campaigns": campaigns,
            "existing_research": existing_research
        }
    
    def _determine_search_queries(self, initiative_data: Dict[str, Any]) -> List[str]:
        """Generate search queries from initiative data"""
        initiative = initiative_data["initiative"]
        queries = []
        
        name = initiative.get("name", "")
        category = initiative.get("category", "")
        objectives = initiative.get("objectives") or {}
        
        if objectives.get("primary"):
            queries.append(f"{objectives['primary']} {category} trends 2024")
        
        if category:
            queries.append(f"latest {category.lower()} marketing strategies")
            queries.append(f"{category.lower()} audience engagement Instagram Facebook")
        
        queries.append(f"{category} competitors social media")
        queries.append(f"trending hashtags {category} 2024")
        
        return queries[:settings.MAX_RESEARCH_QUERIES]
    
    async def _iterative_search(self, queries: List[str], initiative_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute searches and collect results"""
        all_results = []
        unique_urls = set()
        
        for query in queries:
            logger.info(f"Searching: '{query}'")
            try:
                search_results = await self.perplexity.search(query, max_results=5)
                
                for result in search_results:
                    if result.get("url") not in unique_urls:
                        all_results.append({
                            "query": query,
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", ""),
                            "relevance_score": result.get("relevance_score", 0.5)
                        })
                        unique_urls.add(result.get("url"))
                
                logger.info(f"Found {len(search_results)} results")
                
            except Exception as e:
                logger.warning(f"Search failed: {e}")
                continue
        
        return all_results
    
    async def _store_research(self, research_output: Dict[str, Any]):
        """Store validated research in database"""
        research_entry = {
            "initiative_id": self.config.initiative_id,
            "research_type": research_output.get("research_type", "comprehensive"),
            "topic": "automated_research",
            "summary": research_output.get("summary", {}).get("executive_summary", ""),
            "insights": research_output.get("key_findings", []),
            "raw_data": research_output,
            "sources": [s.get("url") for s in research_output.get("sources", [])],
            "relevance_score": {"overall": 0.8},
            "tags": ["automated", "langchain"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "execution_id": self.execution_id,
            "execution_step": self.execution_step
        }
        
        await self.db_client.insert("research", research_entry)
        logger.info("✔ Research stored in database")