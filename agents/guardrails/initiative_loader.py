# agents/guardrails/initiative_loader.py

"""
Centralized data loader for initiative context.
Provides a single source of truth for all guardrail validations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.db.supabase_client import DatabaseClient
import logging
import traceback

logger = logging.getLogger(__name__)


class InitiativeLoader:
    """Loads and caches comprehensive initiative data for guardrail validation"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.db_client = DatabaseClient(initiative_id=initiative_id)
        self._cache = None
        self._cache_timestamp = None
        self.cache_duration = 300  # 5 minutes cache
    
    async def load_full_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Load comprehensive initiative context including all entities and their counts.
        
        Args:
            force_refresh: Force reload even if cache is valid
            
        Returns:
            Dictionary containing full initiative context
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            logger.debug(f"Using cached context for initiative {self.initiative_id}")
            return self._cache
        
        logger.info(f"Loading full context for initiative {self.initiative_id}")
        
        try:
            # Load initiative details
            initiative = await self._load_initiative()
            
            # Load campaigns with active status calculation
            campaigns = await self._load_campaigns_with_status()
            
            # Load ad sets with active status and content counts
            ad_sets = await self._load_ad_sets_with_counts()
            
            # Load all posts
            posts = await self._load_posts()
            
            # Load media files grouped by type
            media_files = await self._load_media_files()
            
            # Load recent research
            research = await self._load_research()
            
            # Calculate aggregate statistics - ENSURE THIS ALWAYS RETURNS VALID DICT
            stats = self._calculate_statistics(campaigns, ad_sets, posts, media_files)
            
            # Build context with guaranteed structure
            context = {
                "initiative": initiative or {},
                "campaigns": campaigns or [],
                "ad_sets": ad_sets or [],
                "posts": posts or [],
                "media_files": media_files or {"images": [], "videos": [], "reels": [], "other": []},
                "research": research or [],
                "statistics": stats,  # Always populated
                "loaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update cache
            self._cache = context
            self._cache_timestamp = datetime.now()
            
            logger.info(f"✅ Context loaded: {len(campaigns)} campaigns, "
                       f"{len(ad_sets)} ad sets, {len(posts)} posts")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to load initiative context: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return a minimal valid context structure on error
            return self._get_empty_context()
    
    def _get_empty_context(self) -> Dict[str, Any]:
        """Return a valid empty context structure"""
        logger.warning("Returning empty context structure due to loading error")
        return {
            "initiative": {},
            "campaigns": [],
            "ad_sets": [],
            "posts": [],
            "media_files": {
                "images": [],
                "videos": [],
                "reels": [],
                "other": []
            },
            "research": [],
            "statistics": {
                "total_campaigns": 0,
                "active_campaigns": 0,
                "total_ad_sets": 0,
                "active_ad_sets": 0,
                "total_posts": 0,
                "published_posts": 0,
                "draft_posts": 0,
                "total_images": 0,
                "total_videos": 0,
                "avg_posts_per_ad_set": 0,
                "avg_ad_sets_per_campaign": 0
            },
            "loaded_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache or not self._cache_timestamp:
            return False
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self.cache_duration
    
    async def _load_initiative(self) -> Dict[str, Any]:
        """Load initiative details"""
        try:
            initiatives = await self.db_client.select(
                "initiatives",
                filters={"id": self.initiative_id}
            )
            
            if not initiatives:
                logger.warning(f"Initiative {self.initiative_id} not found")
                return {}
            
            return initiatives[0]
        except Exception as e:
            logger.error(f"Error loading initiative: {e}")
            return {}
    
    async def _load_campaigns_with_status(self) -> List[Dict[str, Any]]:
        """Load campaigns and calculate their active status"""
        try:
            campaigns = await self.db_client.select(
                "campaigns",
                filters={"initiative_id": self.initiative_id}
            )
            
            if not campaigns:
                logger.info("No campaigns found for initiative")
                return []
            
            now = datetime.now(timezone.utc)
            
            for campaign in campaigns:
                # Determine if campaign is active based on dates and status
                is_active = self._is_entity_active(campaign, now)
                campaign["calculated_active"] = is_active
                
                # Count associated ad sets
                try:
                    ad_sets = await self.db_client.select(
                        "ad_sets",
                        filters={"campaign_id": campaign["id"]}
                    )
                    campaign["ad_set_count"] = len(ad_sets) if ad_sets else 0
                    campaign["active_ad_set_count"] = sum(
                        1 for ad_set in ad_sets 
                        if self._is_entity_active(ad_set, now)
                    ) if ad_sets else 0
                except Exception as e:
                    logger.error(f"Error counting ad sets for campaign {campaign['id']}: {e}")
                    campaign["ad_set_count"] = 0
                    campaign["active_ad_set_count"] = 0
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error loading campaigns: {e}")
            return []
    
    async def _load_ad_sets_with_counts(self) -> List[Dict[str, Any]]:
        """Load ad sets with content counts"""
        try:
            ad_sets = await self.db_client.select(
                "ad_sets",
                filters={"initiative_id": self.initiative_id}
            )
            
            if not ad_sets:
                logger.info("No ad sets found for initiative")
                return []
            
            now = datetime.now(timezone.utc)
            
            for ad_set in ad_sets:
                # Determine active status
                ad_set["calculated_active"] = self._is_entity_active(ad_set, now)
                
                # Count associated posts
                try:
                    posts = await self.db_client.select(
                        "posts",
                        filters={"ad_set_id": ad_set["id"]}
                    )
                    
                    if not posts:
                        posts = []
                    
                    # Count by type
                    facebook_posts = [p for p in posts if p.get("facebook_post_id")]
                    instagram_posts = [p for p in posts if p.get("instagram_post_id")]
                    
                    # Count media
                    photo_count = 0
                    video_count = 0
                    
                    for post in posts:
                        media_urls = post.get("media_urls", [])
                        post_type = post.get("post_type", "")
                        
                        if post_type in ["image", "carousel"]:
                            photo_count += len(media_urls)
                        elif post_type in ["video", "reel"]:
                            video_count += len(media_urls)
                    
                    ad_set["content_counts"] = {
                        "total_posts": len(posts),
                        "facebook_posts": len(facebook_posts),
                        "instagram_posts": len(instagram_posts),
                        "photos": photo_count,
                        "videos": video_count,
                        "draft_posts": sum(1 for p in posts if p.get("status") == "draft"),
                        "published_posts": sum(1 for p in posts if p.get("is_published"))
                    }
                except Exception as e:
                    logger.error(f"Error counting content for ad set {ad_set['id']}: {e}")
                    ad_set["content_counts"] = {
                        "total_posts": 0,
                        "facebook_posts": 0,
                        "instagram_posts": 0,
                        "photos": 0,
                        "videos": 0,
                        "draft_posts": 0,
                        "published_posts": 0
                    }
            
            return ad_sets
            
        except Exception as e:
            logger.error(f"Error loading ad sets: {e}")
            return []
    
    async def _load_posts(self) -> List[Dict[str, Any]]:
        """Load all posts for the initiative"""
        try:
            posts = await self.db_client.select(
                "posts",
                filters={"initiative_id": self.initiative_id}
            )
            
            if not posts:
                logger.info("No posts found for initiative")
                return []
            
            # Enhance with media counts
            for post in posts:
                media_urls = post.get("media_urls", [])
                post["media_count"] = len(media_urls)
                
                # Determine platform
                platforms = []
                if post.get("facebook_post_id"):
                    platforms.append("facebook")
                if post.get("instagram_post_id"):
                    platforms.append("instagram")
                post["platforms"] = platforms
            
            return posts
            
        except Exception as e:
            logger.error(f"Error loading posts: {e}")
            return []
    
    async def _load_media_files(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load media files grouped by type"""
        try:
            media_files = await self.db_client.select(
                "media_files",
                filters={"initiative_id": self.initiative_id}
            )
            
            grouped = {
                "images": [],
                "videos": [],
                "reels": [],
                "other": []
            }
            
            if not media_files:
                logger.info("No media files found for initiative")
                return grouped
            
            for media in media_files:
                file_type = media.get("file_type", "").lower()
                if file_type == "image":
                    grouped["images"].append(media)
                elif file_type == "video":
                    grouped["videos"].append(media)
                elif file_type == "reel":
                    grouped["reels"].append(media)
                else:
                    grouped["other"].append(media)
            
            return grouped
            
        except Exception as e:
            logger.error(f"Error loading media files: {e}")
            return {
                "images": [],
                "videos": [],
                "reels": [],
                "other": []
            }
    
    async def _load_research(self) -> List[Dict[str, Any]]:
        """Load recent research entries"""
        try:
            research = await self.db_client.select(
                "research",
                filters={"initiative_id": self.initiative_id},
                limit=10
            )
            return research if research else []
        except Exception as e:
            logger.error(f"Error loading research: {e}")
            return []
    
    def _is_entity_active(self, entity: Dict[str, Any], now: datetime) -> bool:
        """Determine if an entity is active based on dates and status"""
        if not entity:
            return False
            
        # Check explicit status field
        status = entity.get("status", "").lower()
        if status in ["paused", "stopped", "completed", "archived"]:
            return False
        
        # Check is_active flag
        if "is_active" in entity and not entity["is_active"]:
            return False
        
        # Check date ranges
        start_date = self._parse_datetime(
            entity.get("start_date") or entity.get("start_time")
        )
        end_date = self._parse_datetime(
            entity.get("end_date") or entity.get("end_time")
        )
        
        if start_date and start_date > now:
            return False  # Not started yet
        
        if end_date and end_date < now:
            return False  # Already ended
        
        return True
    
    def _parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if not dt_value:
            return None
        
        if isinstance(dt_value, datetime):
            return dt_value if dt_value.tzinfo else dt_value.replace(tzinfo=timezone.utc)
        
        if isinstance(dt_value, str):
            try:
                # Handle ISO format
                if 'T' in dt_value:
                    dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(dt_value, "%Y-%m-%d")
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse datetime '{dt_value}': {e}")
                return None
        
        return None
    
    def _calculate_statistics(
        self,
        campaigns: List[Dict[str, Any]],
        ad_sets: List[Dict[str, Any]],
        posts: List[Dict[str, Any]],
        media_files: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate aggregate statistics - ALWAYS returns valid dict"""
        try:
            # Handle None/empty inputs
            campaigns = campaigns or []
            ad_sets = ad_sets or []
            posts = posts or []
            media_files = media_files or {}
            
            active_campaigns = [c for c in campaigns if c.get("calculated_active", False)]
            active_ad_sets = [a for a in ad_sets if a.get("calculated_active", False)]
            
            # Calculate averages safely
            avg_posts_per_ad_set = 0
            if ad_sets:
                avg_posts_per_ad_set = len(posts) / len(ad_sets)
            
            avg_ad_sets_per_campaign = 0
            if campaigns:
                avg_ad_sets_per_campaign = len(ad_sets) / len(campaigns)
            
            return {
                "total_campaigns": len(campaigns),
                "active_campaigns": len(active_campaigns),
                "total_ad_sets": len(ad_sets),
                "active_ad_sets": len(active_ad_sets),
                "total_posts": len(posts),
                "published_posts": sum(1 for p in posts if p.get("is_published", False)),
                "draft_posts": sum(1 for p in posts if p.get("status") == "draft"),
                "total_images": len(media_files.get("images", [])),
                "total_videos": len(media_files.get("videos", [])) + len(media_files.get("reels", [])),
                "avg_posts_per_ad_set": avg_posts_per_ad_set,
                "avg_ad_sets_per_campaign": avg_ad_sets_per_campaign
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return valid empty statistics on error
            return {
                "total_campaigns": 0,
                "active_campaigns": 0,
                "total_ad_sets": 0,
                "active_ad_sets": 0,
                "total_posts": 0,
                "published_posts": 0,
                "draft_posts": 0,
                "total_images": 0,
                "total_videos": 0,
                "avg_posts_per_ad_set": 0,
                "avg_ad_sets_per_campaign": 0
            }