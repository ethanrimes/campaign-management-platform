# agents/researcher/agent.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from agents.researcher.tools.perplexity_search import PerplexitySearch  # Updated import path
from backend.db.supabase_client import DatabaseClient
import json
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Focused research agent for gathering search insights"""
    
    def __init__(self, config: AgentConfig):
        # Initialize tools BEFORE calling parent init
        self.perplexity = PerplexitySearch()
        
        # Now call parent init
        super().__init__(config)
        
        # Initialize database client with initiative_id
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize research tools"""
        return [self.perplexity]
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for researcher"""
        return """You are a research analyst specializing in gathering and filtering relevant information.
        Your task is to:
        1. Analyze the initiative's objectives and description
        2. Generate relevant search queries
        3. Filter results for relevance
        4. Return only high-quality, actionable insights
        """
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the research agent with focused functionality"""
        logger.info("=" * 60)
        logger.info("RESEARCH AGENT STARTING")
        logger.info("=" * 60)
        
        # Step 1: Fetch initiative data
        logger.info("\n📊 STEP 1: Fetching initiative data...")
        initiative_data = await self._fetch_initiative_data()
        
        # Step 2: Determine search queries
        logger.info("\n🔍 STEP 2: Determining search queries...")
        search_queries = self._determine_search_queries(initiative_data)
        
        # Step 3: Iteratively search and collect results
        logger.info("\n🌐 STEP 3: Executing searches...")
        all_results = await self._iterative_search(search_queries, initiative_data)
        
        # Step 4: Filter and structure relevant results
        logger.info("\n✨ STEP 4: Filtering relevant results...")
        filtered_insights = self._filter_relevant_results(all_results, initiative_data)
        
        # Step 5: Store research in database
        logger.info("\n💾 STEP 5: Storing research results...")
        await self._store_research(filtered_insights)
        
        logger.info("\n" + "=" * 60)
        logger.info("RESEARCH AGENT COMPLETED")
        logger.info("=" * 60)
        
        return filtered_insights
    
    async def _fetch_initiative_data(self) -> Dict[str, Any]:
        """Fetch and log initiative data"""
        try:
            # Fetch initiative
            initiatives = await self.db_client.select(
                "initiatives",
                filters={"id": self.config.initiative_id}
            )
            
            if not initiatives:
                raise ValueError(f"No initiative found with ID: {self.config.initiative_id}")
            
            initiative = initiatives[0]
            
            # Log preview of fetched data
            logger.info("✓ Initiative fetched successfully")
            logger.info(f"  - Name: {initiative.get('name', 'N/A')}")
            logger.info(f"  - Description: {initiative.get('description', 'N/A')[:100]}...")
            logger.info(f"  - Category: {initiative.get('category', 'N/A')}")
            logger.info(f"  - Optimization Metric: {initiative.get('optimization_metric', 'N/A')}")
            
            # Fetch recent campaigns for context
            campaigns = await self.db_client.select(
                "campaigns",
                filters={
                    "initiative_id": self.config.initiative_id,
                    "is_active": True
                },
                limit=5
            )
            
            logger.info(f"✓ Found {len(campaigns)} active campaign(s)")
            for i, campaign in enumerate(campaigns[:3], 1):
                logger.info(f"  Campaign {i}: {campaign.get('name', 'Unknown')} - {campaign.get('objective', 'N/A')}")
            
            # Fetch previous research for context
            existing_research = await self.db_client.select(
                "research",
                filters={"initiative_id": self.config.initiative_id},
                limit=3
            )
            
            logger.info(f"✓ Found {len(existing_research)} previous research entries")
            
            return {
                "initiative": initiative,
                "campaigns": campaigns,
                "existing_research": existing_research
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch initiative data: {e}")
            raise
    
    def _determine_search_queries(self, initiative_data: Dict[str, Any]) -> List[str]:
        """Determine search queries based on initiative data"""
        initiative = initiative_data["initiative"]
        queries = []
        
        # Extract key information
        name = initiative.get("name", "")
        description = initiative.get("description", "")
        category = initiative.get("category", "")
        objectives = initiative.get("objectives") or {}
        
        logger.info("🧠 Analyzing initiative to generate queries...")
        logger.info(f"  Initiative focus: {category}")
        
        # Generate base queries from objectives
        if objectives.get("primary"):
            base_query = f"{objectives['primary']} {category} trends 2024"
            queries.append(base_query)
            logger.info(f"  Query 1: {base_query}")
        
        # Category-specific queries
        if category:
            category_query = f"latest {category.lower()} marketing strategies social media"
            queries.append(category_query)
            logger.info(f"  Query 2: {category_query}")
            
            engagement_query = f"{category.lower()} audience engagement tactics Instagram Facebook"
            queries.append(engagement_query)
            logger.info(f"  Query 3: {engagement_query}")
        
        # Parse description for key topics
        if description:
            # Extract key phrases (simplified - in production use NLP)
            keywords = [word for word in description.split() if len(word) > 5][:3]
            if keywords:
                keyword_query = f"{' '.join(keywords)} best practices"
                queries.append(keyword_query)
                logger.info(f"  Query 4: {keyword_query}")
        
        # Competitor and trend queries
        competitor_query = f"{category} competitors social media analysis"
        queries.append(competitor_query)
        logger.info(f"  Query 5: {competitor_query}")
        
        # Hashtag research
        hashtag_query = f"trending hashtags {category} 2024"
        queries.append(hashtag_query)
        logger.info(f"  Query 6: {hashtag_query}")
        
        logger.info(f"✓ Generated {len(queries)} search queries")
        
        return queries[:6]  # Limit to 6 queries
    
    async def _iterative_search(self, queries: List[str], initiative_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Iteratively search until sufficient information is gathered"""
        all_results = []
        unique_urls = set()
        max_iterations = 2
        min_results_needed = 15
        
        logger.info(f"🔄 Starting iterative search (target: {min_results_needed} unique results)")
        
        iteration = 1
        for query in queries:
            if len(all_results) >= min_results_needed * 2:  # Stop if we have plenty
                break
                
            logger.info(f"\n  Searching: '{query}'")
            
            try:
                # Search with Perplexity
                search_results = await self.perplexity.search(
                    query=query,
                    max_results=5
                )
                
                # Process results
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
                
                logger.info(f"    ✓ Found {len(search_results)} results")
                
            except Exception as e:
                logger.warning(f"    ⚠ Search failed: {e}")
                continue
        
        # Check if we need more results
        if len(all_results) < min_results_needed and iteration < max_iterations:
            logger.info(f"\n📈 Need more results ({len(all_results)}/{min_results_needed}). Generating additional queries...")
            
            # Generate follow-up queries based on initial results
            follow_up_queries = self._generate_follow_up_queries(all_results, initiative_data)
            
            for query in follow_up_queries[:3]:  # Limit follow-up queries
                logger.info(f"\n  Follow-up search: '{query}'")
                
                try:
                    search_results = await self.perplexity.search(
                        query=query,
                        max_results=5
                    )
                    
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
                    
                    logger.info(f"    ✓ Found {len(search_results)} additional results")
                    
                except Exception as e:
                    logger.warning(f"    ⚠ Follow-up search failed: {e}")
        
        logger.info(f"\n✓ Search completed: {len(all_results)} total results collected")
        
        return all_results
    
    def _generate_follow_up_queries(self, initial_results: List[Dict[str, Any]], initiative_data: Dict[str, Any]) -> List[str]:
        """Generate follow-up queries based on initial results"""
        follow_up_queries = []
        initiative = initiative_data["initiative"]
        
        # Extract common themes from initial results
        common_words = {}
        for result in initial_results:
            words = result.get("snippet", "").lower().split()
            for word in words:
                if len(word) > 6:  # Focus on substantial words
                    common_words[word] = common_words.get(word, 0) + 1
        
        # Get top words not in original queries
        top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if top_words:
            follow_up_queries.append(f"{top_words[0][0]} {initiative.get('category', '')} strategies")
        
        # Add specific platform queries
        follow_up_queries.append(f"Instagram {initiative.get('category', '')} content ideas 2024")
        follow_up_queries.append(f"Facebook advertising {initiative.get('category', '')} best practices")
        
        return follow_up_queries
    
    def _filter_relevant_results(self, all_results: List[Dict[str, Any]], initiative_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter and structure relevant results"""
        initiative = initiative_data["initiative"]
        
        # Define relevance keywords based on initiative
        relevance_keywords = []
        
        # Add category keywords
        if initiative.get("category"):
            relevance_keywords.extend([
                initiative["category"].lower(),
                "marketing", "social media", "engagement", "audience"
            ])
        
        # Add objective keywords
        objectives = initiative.get("objectives") or {}
        if objectives.get("primary"):
            obj_words = objectives["primary"].lower().split()
            relevance_keywords.extend(obj_words)
        
        logger.info(f"🔎 Filtering with keywords: {', '.join(relevance_keywords[:5])}")
        
        # Score and filter results
        scored_results = []
        for result in all_results:
            score = self._calculate_relevance(result, relevance_keywords)
            if score > 0.3:  # Threshold for relevance
                result["final_relevance_score"] = score
                scored_results.append(result)
        
        # Sort by relevance
        scored_results.sort(key=lambda x: x["final_relevance_score"], reverse=True)
        
        # Take top results
        top_results = scored_results[:20]
        
        logger.info(f"✓ Filtered to {len(top_results)} relevant results from {len(all_results)} total")
        
        # Extract insights
        key_findings = []
        recommended_hashtags = set()
        sources = []
        
        for result in top_results[:10]:
            # Create key finding
            finding = {
                "topic": result["query"],
                "finding": result["snippet"],
                "source": result["url"],
                "relevance_score": result["final_relevance_score"]
            }
            key_findings.append(finding)
            sources.append(result["url"])
            
            # Extract hashtags from snippets
            words = result["snippet"].split()
            for word in words:
                if word.startswith("#"):
                    recommended_hashtags.add(word)
        
        # Add default hashtags based on category
        category_hashtags = self._get_category_hashtags(initiative.get("category", ""))
        recommended_hashtags.update(category_hashtags)
        
        # Create summary
        summary = self._generate_summary(key_findings, initiative)
        
        insights = {
            "summary": summary,
            "key_findings": key_findings,
            "content_opportunities": self._identify_opportunities(top_results),
            "recommended_hashtags": list(recommended_hashtags)[:30],
            "sources": sources,
            "total_results_analyzed": len(all_results),
            "relevant_results_found": len(top_results)
        }
        
        # Log summary of findings
        logger.info("\n📊 Research Summary:")
        logger.info(f"  - Key findings: {len(key_findings)}")
        logger.info(f"  - Recommended hashtags: {len(recommended_hashtags)}")
        logger.info(f"  - Content opportunities: {len(insights['content_opportunities'])}")
        
        return insights
    
    def _calculate_relevance(self, result: Dict[str, Any], keywords: List[str]) -> float:
        """Calculate relevance score for a result"""
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
        
        # Normalize score
        normalized = score / max(len(keywords), 1)
        
        # Combine with original relevance score
        original_score = result.get("relevance_score", 0.5)
        final_score = (normalized * 0.7) + (original_score * 0.3)
        
        return min(final_score, 1.0)
    
    def _get_category_hashtags(self, category: str) -> List[str]:
        """Get default hashtags for category"""
        hashtags_map = {
            "Education": ["#education", "#learning", "#edtech", "#students"],
            "Business": ["#business", "#entrepreneur", "#startup", "#growth"],
            "Technology": ["#tech", "#innovation", "#digital", "#technology"],
            "Nonprofit": ["#nonprofit", "#charity", "#community", "#socialimpact"]
        }
        
        return hashtags_map.get(category, ["#socialmedia", "#marketing"])
    
    def _identify_opportunities(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Identify content opportunities from results"""
        opportunities = []
        
        # Look for common themes
        themes = {}
        for result in results:
            snippet = result.get("snippet", "").lower()
            if "video" in snippet:
                themes["video"] = themes.get("video", 0) + 1
            if "story" in snippet or "stories" in snippet:
                themes["stories"] = themes.get("stories", 0) + 1
            if "live" in snippet:
                themes["live"] = themes.get("live", 0) + 1
            if "ugc" in snippet or "user-generated" in snippet:
                themes["ugc"] = themes.get("ugc", 0) + 1
        
        # Create opportunities based on themes
        for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]:
            if theme == "video":
                opportunities.append({
                    "type": "content_format",
                    "description": "Increase video content production based on engagement trends",
                    "priority": "high" if count > 3 else "medium"
                })
            elif theme == "stories":
                opportunities.append({
                    "type": "content_format",
                    "description": "Utilize Instagram/Facebook Stories for time-sensitive content",
                    "priority": "high" if count > 2 else "medium"
                })
            elif theme == "live":
                opportunities.append({
                    "type": "engagement",
                    "description": "Host live sessions for real-time audience interaction",
                    "priority": "medium"
                })
            elif theme == "ugc":
                opportunities.append({
                    "type": "engagement",
                    "description": "Encourage user-generated content through campaigns",
                    "priority": "high"
                })
        
        return opportunities
    
    def _generate_summary(self, findings: List[Dict[str, Any]], initiative: Dict[str, Any]) -> str:
        """Generate research summary"""
        summary = f"Research completed for {initiative.get('name', 'initiative')}. "
        summary += f"Analyzed {len(findings)} key insights related to {initiative.get('category', 'the focus area')}. "
        
        if findings:
            top_finding = findings[0]
            summary += f"Key insight: {top_finding['finding'][:150]}... "
        
        summary += f"The research identifies opportunities in {initiative.get('optimization_metric', 'engagement')} optimization."
        
        return summary
    
    async def _store_research(self, insights: Dict[str, Any]):
        """Store research results in database"""
        try:
            research_entry = {
                "initiative_id": self.config.initiative_id,
                "research_type": "comprehensive",
                "topic": "automated_research",
                "summary": insights["summary"],
                "insights": insights["key_findings"],
                "raw_data": insights,
                "sources": insights["sources"],
                "relevance_score": {"overall": 0.8},
                "tags": ["automated", "perplexity"],
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "execution_id": getattr(self, 'execution_id', None),
            "execution_step": getattr(self, 'execution_step', 'Research')
            }
            
            await self.db_client.insert("research", research_entry)
            logger.info("✓ Research stored in database")
            
        except Exception as e:
            logger.error(f"Failed to store research: {e}")
    
    def validate_output(self, output: Any) -> bool:
        """Validate research output"""
        if not isinstance(output, dict):
            return False
        
        required_fields = ["summary", "key_findings", "recommended_hashtags"]
        return all(field in output for field in required_fields)