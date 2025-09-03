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
        
        # Use sonar-pro model as shown in your curl command
        payload = {
            "model": "sonar-pro",  # Changed from sonar-small-online
            "messages": [
                {
                    "role": "user",
                    "content": query  # Direct query, not "Search for: " prefix
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0  # Increase timeout as sonar-pro may take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data, query)
            else:
                raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")
    
    def _parse_results(self, data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Parse Perplexity API response to extract search results"""
        results = []
        
        # Extract search results from the API response
        search_results = data.get("search_results", [])
        
        # Process each search result
        for i, result in enumerate(search_results[:5]):  # Limit to 5 results
            results.append({
                "title": result.get("title", f"Result {i+1}"),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "date": result.get("date", ""),
                "relevance_score": 1.0 - (i * 0.1),  # Simple relevance scoring
                "source": "perplexity"
            })
        
        # If no search results but we have citations, use those
        if not results and "citations" in data:
            citations = data.get("citations", [])
            for i, citation_url in enumerate(citations[:5]):
                results.append({
                    "title": f"Source {i+1}",
                    "url": citation_url,
                    "snippet": "",  # No snippet available from citations alone
                    "relevance_score": 1.0 - (i * 0.1),
                    "source": "perplexity"
                })
        
        # Also extract key information from the actual response content if needed
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            # You can parse this content for additional insights if needed
            
        return results
    
    async def search_with_context(
        self,
        query: str,
        context: str = "",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform a search with additional context
        
        Returns both search results and the AI-generated response
        """
        if not self.api_key:
            raise ValueError("Perplexity API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Combine context with query if provided
        full_query = f"{context}\n\n{query}" if context else query
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": full_query
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Return both search results and AI response
                return {
                    "search_results": self._parse_results(data, query),
                    "ai_response": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "citations": data.get("citations", []),
                    "usage": data.get("usage", {}),
                    "cost": data.get("usage", {}).get("cost", {})
                }
            else:
                raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")