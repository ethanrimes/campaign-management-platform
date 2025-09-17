
# agents/content_creator/tools/base_tool.py

"""
Base class for content creation tools with stateful validation.
"""

from typing import Optional, Dict, Any
from agents.guardrails.state import ContentGenerationState
import logging

logger = logging.getLogger(__name__)


class ContentCreationTool:
    """Base class for all content creation tools with state management"""
    
    def __init__(self, state: Optional[ContentGenerationState] = None):
        """
        Initialize tool with optional state tracker.
        
        Args:
            state: ContentGenerationState for tracking and validating limits
        """
        self.state = state
        self.validation_enabled = state is not None
        
        if self.validation_enabled:
            logger.info(f"Tool initialized with state tracking for ad_set {state.ad_set_id}")
        else:
            logger.warning("Tool initialized without state tracking - no limit validation!")
    
    def validate_and_update_state(
        self, 
        content_type: str, 
        count: int,
        for_post: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Validate against limits and update state if valid.
        
        Args:
            content_type: Type of content (facebook_posts, instagram_posts, photos, videos)
            count: Number of items to create
            for_post: Whether this is for a single post (applies per-post limits)
            
        Returns:
            (is_valid, error_message)
        """
        if not self.validation_enabled:
            logger.debug("Validation skipped - no state tracker configured")
            return True, None
        
        # Validate based on content type
        if content_type == "facebook_posts":
            is_valid, error = self.state.validate_facebook_post(count)
            if is_valid:
                self.state.add_facebook_posts(count)
                
        elif content_type == "instagram_posts":
            is_valid, error = self.state.validate_instagram_post(count)
            if is_valid:
                self.state.add_instagram_posts(count)
                
        elif content_type == "photos":
            is_valid, error = self.state.validate_photos(count, for_post=for_post)
            if is_valid:
                self.state.add_photos(count)
                
        elif content_type == "videos":
            is_valid, error = self.state.validate_videos(count, for_post=for_post)
            if is_valid:
                self.state.add_videos(count)
                
        else:
            return False, f"Unknown content type: {content_type}"
        
        if not is_valid:
            logger.warning(f"Validation failed: {error}")
        else:
            logger.debug(f"Validated and recorded {count} {content_type}")
        
        return is_valid, error