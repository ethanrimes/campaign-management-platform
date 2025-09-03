# tools/search/facebook_search.py

import httpx
from typing import List, Dict, Any, Optional
import os


class FacebookSearch:
    """Facebook search functionality"""
    
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.app_id = os.getenv("META_APP_ID")
        self.base_url = "https://graph.facebook.com/v18.0"
        
    async def search_pages(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for Facebook pages
        
        Args:
            query: Search query
            category: Page category filter
            limit: Maximum number of results
        """
        if not self.access_token:
            # Return mock data if no access token
            return self._get_mock_pages(query, limit)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "type": "page",
            "q": query,
            "limit": limit
        }
        
        if category:
            params["category"] = category
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_page_results(data)
            else:
                # Fallback to mock data
                return self._get_mock_pages(query, limit)
    
    def _parse_page_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Facebook API response"""
        results = []
        
        for page in data.get("data", []):
            results.append({
                "id": page.get("id"),
                "name": page.get("name"),
                "category": page.get("category"),
                "link": f"https://facebook.com/{page.get('id')}",
                "fan_count": page.get("fan_count", 0)
            })
        
        return results
    
    def _get_mock_pages(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get mock page data for testing"""
        pages = []
        
        for i in range(min(limit, 5)):
            pages.append({
                "id": f"page_{i}",
                "name": f"{query} Page {i+1}",
                "category": "Community",
                "link": f"https://facebook.com/page_{i}",
                "fan_count": 1000 * (i + 1)
            })
        
        return pages
    
    async def get_page_posts(
        self,
        page_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get posts from a Facebook page
        
        Args:
            page_id: Facebook page ID
            limit: Maximum number of posts
        """
        if not self.access_token:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "fields": "message,created_time,likes.summary(true),comments.summary(true)",
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{page_id}/posts",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_post_results(data)
            else:
                return []
    
    def _parse_post_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Facebook post data"""
        results = []
        
        for post in data.get("data", []):
            results.append({
                "id": post.get("id"),
                "message": post.get("message", ""),
                "created_time": post.get("created_time"),
                "likes_count": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments_count": post.get("comments", {}).get("summary", {}).get("total_count", 0)
            })
        
        return results