# agents/content_creator/tools/instagram.py

"""
Instagram posting tools with stateful validation.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Type
from datetime import datetime

from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel

from agents.content_creator.tools.base_tool import ContentCreationTool
from agents.content_creator.tools.models import (
    InstagramImageInput,
    InstagramReelInput,
    PostResponse,
    PostStatus,
    MediaFile,
    MediaType
)
from agents.guardrails.state import ContentGenerationState
from backend.services.media_generation import ImageGenerationService, VideoGenerationService
from backend.services.token_manager import TokenManager
from backend.db.supabase_client import DatabaseClient

logger = logging.getLogger(__name__)


class InstagramImagePostTool(BaseTool, ContentCreationTool):
    """Tool for posting images to Instagram with validation"""
    
    name: str = "instagram_image_post"
    description: str = "Post single or carousel images to Instagram with AI-generated content"
    args_schema: Type[BaseModel] = InstagramImageInput
    
    def __init__(self, state: Optional[ContentGenerationState] = None):
        """Initialize with state tracker"""
        # Initialize both parent classes
        BaseTool.__init__(self)
        ContentCreationTool.__init__(self, state=state)
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        image_prompts: List[str],
        is_carousel: bool = False,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Instagram image posting with validation"""
        try:
            logger.info(f"Instagram image post requested: {len(image_prompts)} images")
            
            # VALIDATION STEP 1: Check if we can create an Instagram post
            is_valid, error = self.validate_and_update_state("instagram_posts", 1)
            if not is_valid:
                logger.error(f"Post limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # VALIDATION STEP 2: Check if we can generate the requested images
            is_valid, error = self.validate_and_update_state(
                "photos", 
                len(image_prompts),
                for_post=True  # Check per-post limit
            )
            if not is_valid:
                # Rollback the post count since we can't create it
                if self.state:
                    self.state.session_instagram_posts -= 1
                    
                logger.error(f"Image limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # Get Instagram tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate images (validation already passed)
            logger.info("Generating images...")
            image_service = ImageGenerationService()
            image_urls = await image_service.generate_images(
                prompts=image_prompts,
                initiative_id=initiative_id,
                num_per_prompt=1
            )
            
            if not image_urls:
                # Rollback state on failure
                if self.state:
                    self.state.session_instagram_posts -= 1
                    self.state.session_photos -= len(image_prompts)
                    
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message="Failed to generate images"
                )
            
            # Rest of the posting logic...
            # (actual Meta API calls would go here)
            
            # Create media file records
            media_files = [
                MediaFile(
                    file_type=MediaType.IMAGE,
                    supabase_path=f"generated-media/{initiative_id}/images/",
                    public_url=url,
                    prompt_used=prompt
                )
                for url, prompt in zip(image_urls, image_prompts)
            ]
            
            # Log remaining capacity
            if self.state:
                remaining = self.state.get_remaining_capacity()
                logger.info(f"Remaining capacity after post: {remaining}")
            
            return PostResponse(
                success=True,
                post_id=f"ig_mock_{datetime.now().timestamp()}",
                post_url=f"https://www.instagram.com/p/mock/",
                status=PostStatus.PUBLISHED,
                media_files=media_files,
                platform="instagram",
                metadata={"remaining_capacity": remaining if self.state else None}
            )
            
        except Exception as e:
            logger.error(f"Instagram image post failed: {e}")
            
            # Rollback state on error
            if self.state:
                self.state.session_instagram_posts = max(0, self.state.session_instagram_posts - 1)
                self.state.session_photos = max(0, self.state.session_photos - len(image_prompts))
            
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="instagram",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method (required by BaseTool)"""
        return asyncio.run(self._arun(*args, **kwargs))


class InstagramReelPostTool(BaseTool, ContentCreationTool):
    """Tool for posting Reels to Instagram with validation"""
    
    name: str = "instagram_reel_post"
    description: str = "Post video Reels to Instagram with AI-generated content"
    args_schema: Type[BaseModel] = InstagramReelInput
    
    def __init__(self, state: Optional[ContentGenerationState] = None):
        """Initialize with state tracker"""
        BaseTool.__init__(self)
        ContentCreationTool.__init__(self, state=state)
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        video_prompt: str,
        duration_seconds: int = 5,
        cover_image_prompt: Optional[str] = None,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Instagram Reel posting with validation"""
        try:
            logger.info("Instagram Reel post requested")
            
            # VALIDATION STEP 1: Check if we can create an Instagram post
            is_valid, error = self.validate_and_update_state("instagram_posts", 1)
            if not is_valid:
                logger.error(f"Post limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # VALIDATION STEP 2: Check if we can generate a video
            is_valid, error = self.validate_and_update_state(
                "videos",
                1,
                for_post=True
            )
            if not is_valid:
                # Rollback post count
                if self.state:
                    self.state.session_instagram_posts -= 1
                    
                logger.error(f"Video limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # VALIDATION STEP 3: If cover image requested, check photo limit
            if cover_image_prompt:
                is_valid, error = self.validate_and_update_state("photos", 1)
                if not is_valid:
                    # Rollback
                    if self.state:
                        self.state.session_instagram_posts -= 1
                        self.state.session_videos -= 1
                    
                    logger.warning(f"Cover image limit reached, proceeding without: {error}")
                    cover_image_prompt = None  # Skip cover image
            
            # Get tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_instagram_tokens()
            
            # Generate video (validation already passed)
            logger.info("Generating video...")
            video_service = VideoGenerationService()
            video_url = await video_service.generate_video(
                prompt=video_prompt,
                initiative_id=initiative_id,
                duration_sec=duration_seconds
            )
            
            if not video_url:
                # Rollback state
                if self.state:
                    self.state.session_instagram_posts -= 1
                    self.state.session_videos -= 1
                    if cover_image_prompt:
                        self.state.session_photos -= 1
                
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message="Failed to generate video"
                )
            
            # Generate cover image if requested and validated
            cover_url = None
            if cover_image_prompt:
                image_service = ImageGenerationService()
                cover_urls = await image_service.generate_images(
                    prompts=[cover_image_prompt],
                    initiative_id=initiative_id
                )
                cover_url = cover_urls[0] if cover_urls else None
            
            # Rest of posting logic...
            
            # Create media file record
            media_files = [
                MediaFile(
                    file_type=MediaType.REEL,
                    supabase_path=f"generated-media/{initiative_id}/videos/",
                    public_url=video_url,
                    prompt_used=video_prompt,
                    duration_seconds=duration_seconds
                )
            ]
            
            # Log remaining capacity
            if self.state:
                remaining = self.state.get_remaining_capacity()
                logger.info(f"Remaining capacity after Reel: {remaining}")
            
            return PostResponse(
                success=True,
                post_id=f"ig_reel_mock_{datetime.now().timestamp()}",
                post_url=f"https://www.instagram.com/reel/mock/",
                status=PostStatus.PUBLISHED,
                media_files=media_files,
                platform="instagram",
                metadata={"remaining_capacity": remaining if self.state else None}
            )
            
        except Exception as e:
            logger.error(f"Instagram Reel post failed: {e}")
            
            # Rollback state
            if self.state:
                self.state.session_instagram_posts = max(0, self.state.session_instagram_posts - 1)
                self.state.session_videos = max(0, self.state.session_videos - 1)
                if cover_image_prompt:
                    self.state.session_photos = max(0, self.state.session_photos - 1)
            
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="instagram",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


# Export tools for easy import
instagram_image_post_tool = InstagramImagePostTool
instagram_reel_post_tool = InstagramReelPostTool