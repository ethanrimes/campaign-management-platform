# agents/content_creator/tools/posting_service.py

"""
Central posting service that orchestrates deterministic execution.
"""

from typing import Dict, Any, List, Optional
from agents.content_creator.tools.base_executor import PostingResult
from agents.content_creator.tools.facebook_executor import FacebookExecutor
from agents.content_creator.tools.instagram_executor import InstagramExecutor
from agents.guardrails.state import ContentGenerationState
import logging
import asyncio

logger = logging.getLogger(__name__)


class PostingService:
    """
    Orchestrates posting to all platforms deterministically.
    Ensures all posts are executed before returning.
    """
    
    def __init__(
        self,
        initiative_id: str,
        state: Optional[ContentGenerationState] = None,
        execution_id: Optional[str] = None
    ):
        self.initiative_id = initiative_id
        self.state = state
        self.execution_id = execution_id
        
        # Initialize executors
        self.facebook_executor = FacebookExecutor(initiative_id, state, execution_id)
        self.instagram_executor = InstagramExecutor(initiative_id, state, execution_id)
    
    async def execute_batch(
        self,
        posts: List[Dict[str, Any]],
        ad_set_id: str,
        placements: Optional[List[str]] = None
    ) -> List[PostingResult]:
        """
        Execute a batch of posts deterministically.
        
        Args:
            posts: List of post dictionaries from ContentBatch
            ad_set_id: Ad set ID these posts belong to
            placements: Optional list of placements to determine platforms
            
        Returns:
            List of PostingResult objects
        """
        logger.info("=" * 70)
        logger.info(f"📦 EXECUTING POST BATCH: {len(posts)} posts for ad_set {ad_set_id}")
        logger.info("=" * 70)
        
        results = []
        
        # Process each post
        for i, post in enumerate(posts, 1):
            logger.info(f"\n📝 Processing post {i}/{len(posts)}: {post.get('post_id')}")
            
            # Determine platforms based on post type and placements
            platforms = self._determine_platforms(post, placements)
            
            # Execute on each platform
            for platform in platforms:
                try:
                    if platform == "facebook":
                        result = await self.facebook_executor.execute(post)
                    elif platform == "instagram":
                        result = await self.instagram_executor.execute(post)
                    else:
                        logger.warning(f"Unknown platform: {platform}")
                        continue
                    
                    results.append(result)
                    
                    if result.success:
                        logger.info(f"✅ Successfully posted to {platform}: {result.platform_post_id}")
                    else:
                        logger.error(f"❌ Failed to post to {platform}: {result.error_message}")
                        # Retry logic could go here
                        
                except Exception as e:
                    logger.error(f"Unexpected error posting to {platform}: {e}")
                    results.append(PostingResult(
                        success=False,
                        post_id=post.get("post_id"),
                        platform=platform,
                        error_message=str(e)
                    ))
        
        # Summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 BATCH EXECUTION COMPLETE")
        logger.info(f"   Total attempts: {len(results)}")
        logger.info(f"   Successful: {len(successful)}")
        logger.info(f"   Failed: {len(failed)}")
        
        if failed:
            logger.error("   Failed posts:")
            for result in failed:
                logger.error(f"     - {result.post_id} on {result.platform}: {result.error_message}")
        
        logger.info("=" * 70)
        
        return results
    
    def _determine_platforms(
        self, 
        post: Dict[str, Any], 
        placements: Optional[List[str]] = None
    ) -> List[str]:
        """
        Determine which platforms to post to based on post type and placements.
        """
        post_type = post.get("post_type", "").lower()
        platforms = []
        
        # If placements specified, use them
        if placements:
            if any("facebook" in p.lower() for p in placements):
                platforms.append("facebook")
            if any("instagram" in p.lower() for p in placements):
                platforms.append("instagram")
        else:
            # Default logic based on post type
            if post_type in ["reel", "story"]:
                # Instagram-only formats
                platforms = ["instagram"]
            elif post_type in ["text", "link"]:
                # Facebook-preferred formats
                platforms = ["facebook"]
            else:
                # Both platforms for images, videos, carousels
                platforms = ["facebook", "instagram"]
        
        return platforms