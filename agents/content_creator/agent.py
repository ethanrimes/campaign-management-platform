# agents/content_creator/agent.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from agents.base.agent import BaseAgent, AgentConfig, AgentOutput
from backend.db.supabase_client import DatabaseClient
import json
import uuid
import random


class ContentCreatorAgent(BaseAgent):
    """Content creation agent for generating social media posts"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.db_client = DatabaseClient(tenant_id=config.tenant_id)
        
    def _initialize_tools(self) -> List[Any]:
        """Initialize content creation tools"""
        # Tools would be initialized here (image/video generation)
        return []
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for content creator"""
        with open("agents/content_creator/prompts/system_prompt.txt", "r") as f:
            return f.read()
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the content creator agent"""
        # Extract ad set information
        ad_set_id = input_data.get("ad_set_id")
        ad_set_data = input_data.get("ad_set_data", {})
        
        # Get additional context
        context = await self._gather_context(ad_set_id)
        
        # Generate content based on creative brief
        posts = await self._generate_posts(ad_set_data, context)
        
        # Process and enhance posts
        enhanced_posts = await self._enhance_posts(posts, context)
        
        # Save posts to database
        await self._save_posts(enhanced_posts, ad_set_id)
        
        return {
            "posts_created": len(enhanced_posts),
            "posts": enhanced_posts
        }
    
    async def _gather_context(self, ad_set_id: str) -> Dict[str, Any]:
        """Gather context for content creation"""
        # Get ad set details
        ad_sets = await self.db_client.select(
            "ad_sets",
            filters={"id": ad_set_id}
        )
        ad_set = ad_sets[0] if ad_sets else {}
        
        # Get campaign details
        if ad_set:
            campaigns = await self.db_client.select(
                "campaigns",
                filters={"id": ad_set.get("campaign_id")}
            )
            campaign = campaigns[0] if campaigns else {}
        else:
            campaign = {}
        
        # Get recent research
        research = await self.db_client.select(
            "research",
            filters={"initiative_id": self.config.initiative_id},
            limit=5
        )
        
        return {
            "ad_set": ad_set,
            "campaign": campaign,
            "research": research
        }
    
    async def _generate_posts(self, ad_set_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate posts based on ad set requirements"""
        creative_brief = ad_set_data.get("creative_brief", {})
        materials = ad_set_data.get("materials", {})
        post_volume = ad_set_data.get("post_volume", 3)
        
        # Prepare prompt for content generation
        prompt = self._create_content_prompt(creative_brief, materials, context)
        
        # Get model config
        from backend.config.settings import settings
        model_config = self.config.llm_config or self._load_model_config()
        
        # Generate posts using LLM
        response = self.client.chat.completions.create(
            model=model_config.model_name,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # Higher for creativity
            max_tokens=model_config.max_tokens,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        generated_content = json.loads(response.choices[0].message.content)
        posts = generated_content.get("posts", [])
        
        # Ensure we have the right number of posts
        while len(posts) < post_volume:
            posts.append(self._create_default_post(creative_brief))
        
        return posts[:post_volume]
    
    def _create_content_prompt(self, creative_brief: Dict[str, Any], materials: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create prompt for content generation"""
        campaign = context.get("campaign", {})
        research = context.get("research", [])
        
        # Extract hashtags from recent research
        hashtags = []
        for r in research:
            if r.get("raw_data", {}).get("recommended_hashtags"):
                hashtags.extend(r["raw_data"]["recommended_hashtags"][:10])
        
        prompt = f"""
        Create {creative_brief.get('post_count', 3)} social media posts based on the following:
        
        Campaign Objective: {campaign.get('objective', 'ENGAGEMENT')}
        Campaign Name: {campaign.get('name', 'Campaign')}
        
        Creative Brief:
        - Theme: {creative_brief.get('theme', 'General')}
        - Tone: {creative_brief.get('tone', 'Professional')}
        - Format: {creative_brief.get('format', 'Mixed')}
        - Target Audience: {creative_brief.get('target_audience', 'General')}
        
        Available Materials:
        - Links: {json.dumps(materials.get('links', []))}
        - Hashtags: {json.dumps(list(set(hashtags))[:20])}
        - Brand Assets: {json.dumps(materials.get('assets', []))}
        
        Please generate posts with the following structure:
        {{
            "posts": [
                {{
                    "post_type": "image|video|carousel|story",
                    "text_content": "Caption text with emojis",
                    "hashtags": ["hashtag1", "hashtag2"],
                    "links": ["link1"],
                    "media_description": "Description of visual content needed",
                    "call_to_action": "CTA text",
                    "scheduled_time": "ISO datetime"
                }}
            ]
        }}
        
        Make each post unique, engaging, and aligned with the campaign objectives.
        """
        
        return prompt
    
    def _create_default_post(self, creative_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create a default post structure"""
        post_types = ["image", "video", "carousel"]
        
        return {
            "post_type": random.choice(post_types),
            "text_content": f"Exciting update about {creative_brief.get('theme', 'our initiative')}! 🚀",
            "hashtags": ["#community", "#engagement", "#socialmedia"],
            "links": [],
            "media_description": "Engaging visual content",
            "call_to_action": "Learn more",
            "scheduled_time": (datetime.utcnow() + timedelta(days=random.randint(1, 7))).isoformat()
        }
    
    async def _enhance_posts(self, posts: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance posts with additional formatting and media"""
        enhanced_posts = []
        
        for post in posts:
            # Add platform-specific formatting
            enhanced_post = post.copy()
            
            # Ensure hashtags are properly formatted
            hashtags = post.get("hashtags", [])
            enhanced_post["hashtags"] = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            
            # Add emoji enhancement
            if "🎯" not in enhanced_post["text_content"]:
                enhanced_post["text_content"] = self._add_emojis(enhanced_post["text_content"])
            
            # Generate media URLs (placeholder - would call actual generation tools)
            enhanced_post["media_urls"] = await self._generate_media(
                post["post_type"],
                post.get("media_description", "")
            )
            
            # Add metadata
            enhanced_post["generation_metadata"] = {
                "model": self.config.model_provider,
                "generated_at": datetime.utcnow().isoformat(),
                "agent_id": self.agent_id
            }
            
            enhanced_posts.append(enhanced_post)
        
        return enhanced_posts
    
    def _add_emojis(self, text: str) -> str:
        """Add relevant emojis to text"""
        emoji_map = {
            "exciting": "🎉",
            "new": "✨",
            "learn": "📚",
            "join": "🤝",
            "discover": "🔍",
            "update": "📢",
            "success": "🏆",
            "community": "👥"
        }
        
        text_lower = text.lower()
        for word, emoji in emoji_map.items():
            if word in text_lower and emoji not in text:
                text += f" {emoji}"
                break
        
        return text
    
    async def _generate_media(self, post_type: str, description: str) -> List[str]:
        """Generate media URLs (placeholder implementation)"""
        # In production, this would call actual image/video generation tools
        # For now, return placeholder URLs
        
        if post_type == "image":
            return [f"https://placeholder.com/image_{uuid.uuid4().hex[:8]}.jpg"]
        elif post_type == "video":
            return [f"https://placeholder.com/video_{uuid.uuid4().hex[:8]}.mp4"]
        elif post_type == "carousel":
            return [
                f"https://placeholder.com/carousel_{i}_{uuid.uuid4().hex[:8]}.jpg"
                for i in range(3)
            ]
        else:
            return []
    
    async def _save_posts(self, posts: List[Dict[str, Any]], ad_set_id: str):
        """Save generated posts to database"""
        for post in posts:
            post_entry = {
                "tenant_id": self.config.tenant_id,
                "ad_set_id": ad_set_id,
                "post_type": post["post_type"],
                "text_content": post["text_content"],
                "hashtags": post["hashtags"],
                "links": post.get("links", []),
                "media_urls": post.get("media_urls", []),
                "media_metadata": {
                    "description": post.get("media_description", "")
                },
                "scheduled_time": post.get("scheduled_time"),
                "status": "draft",
                "generation_metadata": post.get("generation_metadata", {})
            }
            
            await self.db_client.insert("posts", post_entry)
    
    def validate_output(self, output: Any) -> bool:
        """Validate content creator output"""
        if not isinstance(output, dict):
            return False
        
        if "posts" not in output:
            return False
        
        posts = output["posts"]
        if not isinstance(posts, list):
            return False
        
        # Validate each post has required fields
        for post in posts:
            required_fields = ["post_type", "text_content"]
            if not all(field in post for field in required_fields):
                return False
        
        return True