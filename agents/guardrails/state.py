# agents/guardrails/state.py

"""
Stateful tracking for content generation to enforce limits.
Maintains counts and validates against configured limits.
"""

from typing import Dict, Any, Optional, Tuple
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ContentGenerationState:
    """
    Tracks content generation state for an ad set to enforce limits.
    This is a stateful class that maintains counts during generation.
    """
    
    def __init__(self, ad_set_id: str, initial_counts: Dict[str, int]):
        """
        Initialize state tracker with current counts for an ad set.
        
        Args:
            ad_set_id: The ad set being tracked
            initial_counts: Current counts from database, e.g.:
                {
                    "facebook_posts": 2,
                    "instagram_posts": 3,
                    "photos": 10,
                    "videos": 1
                }
        """
        self.ad_set_id = ad_set_id
        
        # Initialize counts from database
        self.facebook_posts = initial_counts.get("facebook_posts", 0)
        self.instagram_posts = initial_counts.get("instagram_posts", 0)
        self.photos = initial_counts.get("photos", 0)
        self.videos = initial_counts.get("videos", 0)
        
        # Track counts for this generation session
        self.session_facebook_posts = 0
        self.session_instagram_posts = 0
        self.session_photos = 0
        self.session_videos = 0
        
        # Load limits from settings
        self.limits = {
            "facebook_posts": settings.MAX_FACEBOOK_POSTS_PER_AD_SET,
            "instagram_posts": settings.MAX_INSTAGRAM_POSTS_PER_AD_SET,
            "photos": settings.MAX_PHOTOS_PER_AD_SET,
            "videos": settings.MAX_VIDEOS_PER_AD_SET,
            "photos_per_post": settings.MAX_PHOTOS_PER_POST,
            "videos_per_post": settings.MAX_VIDEOS_PER_POST
        }
        
        logger.info(f"ContentGenerationState initialized for ad_set {ad_set_id}")
        logger.info(f"  Current counts: FB posts={self.facebook_posts}, "
                   f"IG posts={self.instagram_posts}, photos={self.photos}, videos={self.videos}")
        logger.info(f"  Limits: {self.limits}")
    
    def validate_facebook_post(self, num_posts: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Validate if we can create more Facebook posts.
        
        Args:
            num_posts: Number of posts to create
            
        Returns:
            (is_valid, error_message)
        """
        total_after = self.facebook_posts + self.session_facebook_posts + num_posts
        
        if total_after > self.limits["facebook_posts"]:
            remaining = self.limits["facebook_posts"] - (self.facebook_posts + self.session_facebook_posts)
            return False, (
                f"Facebook post limit exceeded for ad_set {self.ad_set_id}. "
                f"Limit: {self.limits['facebook_posts']}, "
                f"Current: {self.facebook_posts + self.session_facebook_posts}, "
                f"Requested: {num_posts}, "
                f"Remaining: {max(0, remaining)}"
            )
        
        return True, None
    
    def validate_instagram_post(self, num_posts: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Validate if we can create more Instagram posts.
        
        Args:
            num_posts: Number of posts to create
            
        Returns:
            (is_valid, error_message)
        """
        total_after = self.instagram_posts + self.session_instagram_posts + num_posts
        
        if total_after > self.limits["instagram_posts"]:
            remaining = self.limits["instagram_posts"] - (self.instagram_posts + self.session_instagram_posts)
            return False, (
                f"Instagram post limit exceeded for ad_set {self.ad_set_id}. "
                f"Limit: {self.limits['instagram_posts']}, "
                f"Current: {self.instagram_posts + self.session_instagram_posts}, "
                f"Requested: {num_posts}, "
                f"Remaining: {max(0, remaining)}"
            )
        
        return True, None
    
    def validate_photos(self, num_photos: int, for_post: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate if we can generate more photos.
        
        Args:
            num_photos: Number of photos to generate
            for_post: If True, validates against per-post limit
            
        Returns:
            (is_valid, error_message)
        """
        # Check per-post limit if applicable
        if for_post and num_photos > self.limits["photos_per_post"]:
            return False, (
                f"Photos per post limit exceeded. "
                f"Limit: {self.limits['photos_per_post']}, "
                f"Requested: {num_photos}"
            )
        
        # Check overall ad set limit
        total_after = self.photos + self.session_photos + num_photos
        
        if total_after > self.limits["photos"]:
            remaining = self.limits["photos"] - (self.photos + self.session_photos)
            return False, (
                f"Photo limit exceeded for ad_set {self.ad_set_id}. "
                f"Limit: {self.limits['photos']}, "
                f"Current: {self.photos + self.session_photos}, "
                f"Requested: {num_photos}, "
                f"Remaining: {max(0, remaining)}"
            )
        
        return True, None
    
    def validate_videos(self, num_videos: int, for_post: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate if we can generate more videos.
        
        Args:
            num_videos: Number of videos to generate
            for_post: If True, validates against per-post limit
            
        Returns:
            (is_valid, error_message)
        """
        # Check per-post limit if applicable
        if for_post and num_videos > self.limits["videos_per_post"]:
            return False, (
                f"Videos per post limit exceeded. "
                f"Limit: {self.limits['videos_per_post']}, "
                f"Requested: {num_videos}"
            )
        
        # Check overall ad set limit
        total_after = self.videos + self.session_videos + num_videos
        
        if total_after > self.limits["videos"]:
            remaining = self.limits["videos"] - (self.videos + self.session_videos)
            return False, (
                f"Video limit exceeded for ad_set {self.ad_set_id}. "
                f"Limit: {self.limits['videos']}, "
                f"Current: {self.videos + self.session_videos}, "
                f"Requested: {num_videos}, "
                f"Remaining: {max(0, remaining)}"
            )
        
        return True, None
    
    def add_facebook_posts(self, count: int = 1):
        """Record Facebook posts as created"""
        self.session_facebook_posts += count
        logger.debug(f"Added {count} Facebook posts. Session total: {self.session_facebook_posts}")
    
    def add_instagram_posts(self, count: int = 1):
        """Record Instagram posts as created"""
        self.session_instagram_posts += count
        logger.debug(f"Added {count} Instagram posts. Session total: {self.session_instagram_posts}")
    
    def add_photos(self, count: int):
        """Record photos as generated"""
        self.session_photos += count
        logger.debug(f"Added {count} photos. Session total: {self.session_photos}")
    
    def add_videos(self, count: int):
        """Record videos as generated"""
        self.session_videos += count
        logger.debug(f"Added {count} videos. Session total: {self.session_videos}")
    
    def get_remaining_capacity(self) -> Dict[str, int]:
        """Get remaining capacity for each content type"""
        return {
            "facebook_posts": max(0, self.limits["facebook_posts"] - 
                                (self.facebook_posts + self.session_facebook_posts)),
            "instagram_posts": max(0, self.limits["instagram_posts"] - 
                                 (self.instagram_posts + self.session_instagram_posts)),
            "photos": max(0, self.limits["photos"] - 
                       (self.photos + self.session_photos)),
            "videos": max(0, self.limits["videos"] - 
                       (self.videos + self.session_videos))
        }
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of this generation session"""
        return {
            "ad_set_id": self.ad_set_id,
            "session_created": {
                "facebook_posts": self.session_facebook_posts,
                "instagram_posts": self.session_instagram_posts,
                "photos": self.session_photos,
                "videos": self.session_videos
            },
            "total_counts": {
                "facebook_posts": self.facebook_posts + self.session_facebook_posts,
                "instagram_posts": self.instagram_posts + self.session_instagram_posts,
                "photos": self.photos + self.session_photos,
                "videos": self.videos + self.session_videos
            },
            "remaining_capacity": self.get_remaining_capacity()
        }
    
    def reset_session(self):
        """Reset session counts (useful for retry scenarios)"""
        self.session_facebook_posts = 0
        self.session_instagram_posts = 0
        self.session_photos = 0
        self.session_videos = 0
        logger.debug(f"Session counts reset for ad_set {self.ad_set_id}")


class InitiativeGenerationState:
    """
    Manages generation state across multiple ad sets in an initiative.
    """
    
    def __init__(self, initiative_id: str, ad_set_counts: Dict[str, Dict[str, int]]):
        """
        Initialize state for an entire initiative.
        
        Args:
            initiative_id: The initiative being processed
            ad_set_counts: Dictionary mapping ad_set_id to content counts
        """
        self.initiative_id = initiative_id
        self.ad_set_states = {}
        
        # Create state tracker for each ad set
        for ad_set_id, counts in ad_set_counts.items():
            self.ad_set_states[ad_set_id] = ContentGenerationState(ad_set_id, counts)
        
        logger.info(f"InitiativeGenerationState initialized with {len(self.ad_set_states)} ad sets")
    
    def get_ad_set_state(self, ad_set_id: str) -> Optional[ContentGenerationState]:
        """Get state tracker for a specific ad set"""
        return self.ad_set_states.get(ad_set_id)
    
    def get_all_summaries(self) -> Dict[str, Any]:
        """Get summaries for all ad sets"""
        return {
            "initiative_id": self.initiative_id,
            "ad_sets": {
                ad_set_id: state.get_session_summary()
                for ad_set_id, state in self.ad_set_states.items()
            }
        }