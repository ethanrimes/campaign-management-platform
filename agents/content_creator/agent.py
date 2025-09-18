# agents/content_creator/agent.py

from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel
from agents.base.agent import BaseAgent, AgentConfig
from agents.content_creator.models import ContentBatch
from agents.content_creator.prompt_builder import ContentCreatorPromptBuilder
from agents.content_creator.tools.facebook import (
    FacebookTextLinkPostTool, FacebookImagePostTool, FacebookVideoPostTool
)
from agents.content_creator.tools.instagram import (
    InstagramImagePostTool, InstagramReelPostTool
)
from backend.db.supabase_client import DatabaseClient
from agents.guardrails.state import ContentGenerationState, InitiativeGenerationState
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """Content creator with structured output and guardrails"""
    
    def __init__(self, config: AgentConfig):
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.prompt_builder = ContentCreatorPromptBuilder(config.initiative_id)
        self.generation_state = None  # Injected by orchestrator
        self.tools_by_ad_set = {}
        super().__init__(config)
    
    def _initialize_tools(self) -> List[Any]:
        """Tools are initialized per ad_set"""
        return []
    
    def get_output_model(self) -> Type[BaseModel]:
        """Return ContentBatch model for structured output"""
        return ContentBatch
    
    def get_system_prompt(self) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.get_system_prompt()
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build user prompt using fresh context from input_data"""
        # Get fresh campaigns from context instead of input
        context = input_data.get("context", {})
        
        # Extract active campaigns with their ad sets
        campaigns = []
        for campaign in context.get("campaigns", []):
            if campaign.get("calculated_active", False) or campaign.get("is_active", False):
                # Get ad sets for this campaign
                campaign_ad_sets = [
                    ad_set for ad_set in context.get("ad_sets", [])
                    if ad_set.get("campaign_id") == campaign.get("id") and
                    (ad_set.get("calculated_active", False) or ad_set.get("is_active", False))
                ]
                
                if campaign_ad_sets:
                    campaigns.append({
                        "id": campaign["id"],
                        "name": campaign["name"],
                        "objective": campaign.get("objective"),
                        "ad_sets": campaign_ad_sets
                    })
        
        # If we have fresh campaigns from context, use them
        # Otherwise fall back to input campaigns (for backwards compatibility)
        if not campaigns:
            campaigns = input_data.get("campaigns", [])
        
        # Get the specific ad set we're creating content for
        ad_set = input_data.get("ad_set", {})
        campaign = input_data.get("campaign", {})
        
        # If ad_set is provided, we're processing a specific one
        if ad_set:
            # Update remaining capacity from fresh context
            ad_set_id = ad_set.get("id")
            fresh_ad_set = next(
                (a for a in context.get("ad_sets", []) if a["id"] == ad_set_id),
                ad_set
            )
            
            # Calculate remaining capacity
            content_counts = fresh_ad_set.get("content_counts", {})
            remaining_capacity = {
                'facebook_posts': settings.MAX_FACEBOOK_POSTS_PER_AD_SET - content_counts.get('facebook_posts', 0),
                'instagram_posts': settings.MAX_INSTAGRAM_POSTS_PER_AD_SET - content_counts.get('instagram_posts', 0),
                'photos': settings.MAX_PHOTOS_PER_AD_SET - content_counts.get('photos', 0),
                'videos': settings.MAX_VIDEOS_PER_AD_SET - content_counts.get('videos', 0)
            }
            
            # Update input data with fresh values
            input_data = {
                **input_data,
                "ad_set": fresh_ad_set,
                "context": {
                    **input_data.get("context", {}),
                    "remaining_capacity": remaining_capacity
                }
            }
        
        # Delegate to existing prompt builder with updated data
        return self.prompt_builder.build_user_prompt(input_data, error_feedback)
    
    def validate_output(self, output: Any) -> bool:
        """Validate ContentBatch structure"""
        if not isinstance(output, dict):
            return False
        
        # Check required fields for ContentBatch
        required_fields = ["batch_id", "ad_set_id", "posts", "theme", "target_audience"]
        if not all(field in output for field in required_fields):
            return False
        
        # Check posts array
        posts = output.get("posts", [])
        if not isinstance(posts, list) or len(posts) == 0:
            return False
        
        # Each post should have required fields
        for post in posts:
            if not isinstance(post, dict):
                return False
            
            post_required = ["post_id", "post_type", "content", "schedule"]
            if not all(field in post for field in post_required):
                return False
        
        return True
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content creation with enhanced logging"""
        logger.info("=" * 70)
        logger.info("CONTENT CREATOR STARTING (WITH GUARDRAILS)")
        logger.info("=" * 70)
        
        # Get initial context
        initial_context = await self.initiative_loader.load_full_context()
        
        # Extract campaigns with detailed logging
        campaigns = []
        for campaign in initial_context.get("campaigns", []):
            if campaign.get("calculated_active", False) or campaign.get("is_active", False):
                campaign_ad_sets = [
                    ad_set for ad_set in initial_context.get("ad_sets", [])
                    if ad_set.get("campaign_id") == campaign.get("id") and
                    (ad_set.get("calculated_active", False) or ad_set.get("is_active", False))
                ]
                if campaign_ad_sets:
                    campaigns.append({
                        "id": campaign["id"],
                        "name": campaign["name"], 
                        "objective": campaign.get("objective"),
                        "ad_sets": campaign_ad_sets
                    })
        
        if not campaigns:
            campaigns = input_data.get("campaigns", [])
        
        if not campaigns:
            logger.warning("No campaigns provided to content creator")
            return {"posts_created": 0, "posts": [], "errors": ["No campaigns provided"]}
        
        logger.info(f"📋 Found {len(campaigns)} active campaigns to process")
        
        # Initialize generation state
        ad_set_counts = {}
        for ad_set in initial_context.get("ad_sets", []):
            counts = ad_set.get("content_counts", {})
            ad_set_counts[ad_set["id"]] = {
                "facebook_posts": counts.get("facebook_posts", 0),
                "instagram_posts": counts.get("instagram_posts", 0),
                "photos": counts.get("photos", 0),
                "videos": counts.get("videos", 0)
            }
        
        self.generation_state = InitiativeGenerationState(
            self.config.initiative_id,
            ad_set_counts
        )
        
        all_posts = []
        all_errors = []
        
        # Process each campaign and ad set with detailed logging
        for campaign in campaigns:
            campaign_name = campaign.get("name", "Unknown")
            campaign_id = campaign.get("id", "Unknown")
            
            logger.info(f"\n📋 Processing Campaign: {campaign_name}")
            logger.info(f"   ID: {campaign_id}")
            logger.info(f"   Objective: {campaign.get('objective', 'Not specified')}")
            logger.info(f"   Ad Sets: {len(campaign.get('ad_sets', []))}")
            
            for ad_set in campaign.get("ad_sets", []):
                ad_set_id = ad_set.get("id")
                ad_set_name = ad_set.get("name", "Unknown")
                
                if not ad_set_id:
                    continue
                
                logger.info(f"\n  📍 Ad Set: {ad_set_name}")
                logger.info(f"     ID: {ad_set_id}")
                logger.info(f"     Placements: {ad_set.get('placements', [])}")
                logger.info(f"     Post Volume: {ad_set.get('post_volume', 'not specified')}")
                logger.info(f"     Post Frequency: {ad_set.get('post_frequency', 'not specified')}/week")
                
                # Show current content counts
                if ad_set_id in ad_set_counts:
                    counts = ad_set_counts[ad_set_id]
                    logger.info(f"     Current Content:")
                    logger.info(f"       - Facebook posts: {counts['facebook_posts']}")
                    logger.info(f"       - Instagram posts: {counts['instagram_posts']}")
                    logger.info(f"       - Photos: {counts['photos']}")
                    logger.info(f"       - Videos: {counts['videos']}")
                
                # Create input for this specific ad set
                ad_set_input = {
                    "ad_set": ad_set,
                    "campaign": campaign,
                    "campaigns": campaigns
                }
                
                try:
                    logger.info(f"     🚀 Generating content...")
                    
                    # Execute with retries
                    content_batch = await self.execute_with_retries(ad_set_input)
                    
                    # Safely get posts, defaulting to empty list
                    posts = content_batch.get("posts", []) if content_batch else []
                    
                    if posts:
                        logger.info(f"     ✅ Generated {len(posts)} posts:")
                        
                        # Count by platform and type
                        fb_count = 0
                        ig_count = 0
                        post_types = {}
                        
                        for i, post in enumerate(posts, 1):
                            post_type = post.get("post_type", "unknown")
                            post_types[post_type] = post_types.get(post_type, 0) + 1
                            
                            # Determine platforms based on placement/type
                            platforms = []
                            placements = ad_set.get("placements") or []
                            
                            if any("facebook" in p.lower() for p in placements):
                                fb_count += 1
                                platforms.append("Facebook")
                            if any("instagram" in p.lower() for p in placements):
                                ig_count += 1
                                platforms.append("Instagram")
                            
                            # If no specific placements, assume both
                            if not platforms:
                                if post_type in ["reel", "story"]:
                                    platforms = ["Instagram"]
                                    ig_count += 1
                                else:
                                    platforms = ["Facebook", "Instagram"]
                                    fb_count += 1
                                    ig_count += 1
                            
                            logger.info(f"       Post {i}:")
                            logger.info(f"         - Type: {post_type}")
                            logger.info(f"         - Platforms: {', '.join(platforms)}")
                            logger.info(f"         - Status: {post.get('status', 'draft')}")
                            
                            media = post.get("media", [])
                            if media:
                                logger.info(f"         - Media: {len(media)} items")
                        
                        # Summary for this ad set
                        logger.info(f"     📊 Generation Summary:")
                        logger.info(f"       - Facebook posts: {fb_count}")
                        logger.info(f"       - Instagram posts: {ig_count}")
                        logger.info(f"       - Post types: {post_types}")
                        
                        # Show remaining capacity
                        if self.generation_state:
                            ad_set_state = self.generation_state.get_ad_set_state(ad_set_id)
                            if ad_set_state:
                                remaining = ad_set_state.get_remaining_capacity()
                                logger.info(f"     📦 Remaining Capacity:")
                                logger.info(f"       - FB posts: {remaining.get('facebook_posts', 0)}")
                                logger.info(f"       - IG posts: {remaining.get('instagram_posts', 0)}")
                                logger.info(f"       - Photos: {remaining.get('photos', 0)}")
                                logger.info(f"       - Videos: {remaining.get('videos', 0)}")
                        
                        all_posts.extend(posts)
                    
                        # Save posts
                        await self._save_posts_to_db(posts, ad_set_id, campaign.get("id"))
                    else:
                        logger.warning(f"     ⚠️ No posts generated")
                    
                except Exception as e:
                    error_msg = f"Failed for ad set {ad_set_name}: {str(e)}"
                    all_errors.append(error_msg)
                    logger.error(f"     ❌ {error_msg}")
        
        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("CONTENT CREATION COMPLETED")
        logger.info("=" * 70)
        logger.info(f"📊 Final Results:")
        logger.info(f"  - Total posts created: {len(all_posts)}")
        logger.info(f"  - Total errors: {len(all_errors)}")
        
        if all_errors:
            logger.error(f"  - Errors encountered:")
            for err in all_errors[:5]:  # Show first 5 errors
                logger.error(f"    • {err}")
        
        logger.info("=" * 70)
        
        return {
            "posts_created": len(all_posts),
            "posts": all_posts,
            "errors": all_errors,
            "generation_summary": self.generation_state.get_all_summaries() if self.generation_state else {}
        }
    
    def _get_or_create_tools(self, ad_set_id: str) -> Dict[str, Any]:
        """Get or create tools with state validation"""
        if ad_set_id not in self.tools_by_ad_set:
            ad_set_state = None
            if self.generation_state:
                ad_set_state = self.generation_state.get_ad_set_state(ad_set_id)
            
            self.tools_by_ad_set[ad_set_id] = {
                'facebook_text': FacebookTextLinkPostTool(state=ad_set_state),
                'facebook_image': FacebookImagePostTool(state=ad_set_state),
                'facebook_video': FacebookVideoPostTool(state=ad_set_state),
                'instagram_image': InstagramImagePostTool(state=ad_set_state),
                'instagram_reel': InstagramReelPostTool(state=ad_set_state)
            }
            
            # Pass execution tracking
            for tool in self.tools_by_ad_set[ad_set_id].values():
                tool.execution_id = self.execution_id
                tool.execution_step = self.execution_step
        
        return self.tools_by_ad_set[ad_set_id]
    
    async def _gather_context(self, ad_set_id: str) -> Dict[str, Any]:
        """Gather context including remaining capacity"""
        ad_sets = await self.db_client.select("ad_sets", filters={"id": ad_set_id})
        ad_set = ad_sets[0] if ad_sets else {}
        
        campaigns = []
        if ad_set:
            campaigns = await self.db_client.select(
                "campaigns",
                filters={"id": ad_set.get("campaign_id")}
            )
        
        remaining_capacity = {}
        if self.generation_state:
            ad_set_state = self.generation_state.get_ad_set_state(ad_set_id)
            if ad_set_state:
                remaining_capacity = ad_set_state.get_remaining_capacity()
                logger.info(f"  Remaining capacity: {remaining_capacity}")
        
        return {
            "ad_set": ad_set,
            "campaign": campaigns[0] if campaigns else {},
            "remaining_capacity": remaining_capacity
        }
    
    def _validate_content_batch(self, batch: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate content against remaining capacity"""
        remaining = context.get("remaining_capacity", {})
        
        if not remaining:
            logger.warning("No capacity information available, proceeding with content")
            return True
        
        # Count posts by type
        facebook_count = 0
        instagram_count = 0
        
        for post in batch.get("posts", []):
            post_type = post.get("post_type", "").lower()
            # Simple heuristic - in reality, check platform_ids or placements
            if "reel" in post_type or "story" in post_type:
                instagram_count += 1
            else:
                # Could be both platforms
                facebook_count += 1
                instagram_count += 1
        
        # Check limits
        if facebook_count > remaining.get('facebook_posts', 0):
            logger.warning(f"Facebook post limit exceeded: {facebook_count} > {remaining.get('facebook_posts', 0)}")
            return False
        if instagram_count > remaining.get('instagram_posts', 0):
            logger.warning(f"Instagram post limit exceeded: {instagram_count} > {remaining.get('instagram_posts', 0)}")
            return False
        
        return True
    
    def _sanitize_llm_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate all UUIDs for content creator output"""
        import uuid
        
        # Fix batch_id
        if "batch_id" in output:
            output["batch_id"] = str(uuid.uuid4())
        
        # Fix posts
        if "posts" in output:
            for post in output["posts"]:
                post["post_id"] = str(uuid.uuid4())
        
        return output
    
    async def _execute_content_batch(
        self, batch: Dict[str, Any], ad_set_id: str, tools: Dict[str, Any]
    ) -> tuple[List[Dict], List[str]]:
        """Execute content creation with tools (simplified for now)"""
        posts = []
        errors = []
        
        for post in batch.get("posts", []):
            try:
                # For now, just add the post as-is
                # In production, would route to appropriate tool based on post type
                posts.append(post)
                logger.info(f"    ✔ Created {post.get('post_type')} post: {post.get('post_id')}")
            except Exception as e:
                errors.append(str(e))
        
        return posts, errors
    
    async def _save_posts_to_db(self, posts: List[Dict], ad_set_id: str, campaign_id: str):
        """Save posts to database"""
        for post in posts:
            try:
                post_entry = {
                    "id": post.get("post_id"),
                    "ad_set_id": ad_set_id,
                    "campaign_id": campaign_id,
                    "initiative_id": self.config.initiative_id,
                    "post_type": post.get("post_type"),
                    "text_content": post.get("content", {}).get("caption", ""),
                    "hashtags": post.get("content", {}).get("hashtags", []),
                    "status": post.get("status", "draft"),
                    "is_published": False,
                    "execution_id": self.execution_id
                }
                
                await self.db_client.insert("posts", post_entry)
                
            except Exception as e:
                logger.error(f"Failed to save post {post.get('post_id')}: {e}")