
# tools/search/perplexity_search.py

import os
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class PerplexitySearch:
    """Perplexity API integration for web search"""
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"
        
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "general"
    ) -> List[Dict[str, Any]]:
        """
        Perform a search using Perplexity API
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_type: Type of search (general, academic, news)
        """
        if not self.api_key:
            raise ValueError("Perplexity API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-small-online",
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for: {query}"
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.2,
            "return_citations": True,
            "search_domain_filter": [search_type] if search_type != "general" else None
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data, query)
            else:
                raise Exception(f"Perplexity API error: {response.status_code}")
    
    def _parse_results(self, data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Parse Perplexity API response"""
        results = []
        
        # Extract content and citations
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            # Create structured results
            for i, citation in enumerate(citations[:5]):  # Limit to 5 results
                results.append({
                    "title": citation.get("title", f"Result {i+1}"),
                    "url": citation.get("url", ""),
                    "snippet": citation.get("snippet", ""),
                    "relevance_score": 1.0 - (i * 0.1),  # Simple relevance scoring
                    "source": "perplexity"
                })
        
        return results