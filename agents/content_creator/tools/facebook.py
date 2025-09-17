# agents/content_creator/tools/facebook.py

"""
Facebook posting tools with stateful validation and guardrails.
Prevents excessive content generation through limit enforcement.
"""

import asyncio
import logging
import json
from typing import List, Optional, Dict, Any, Type
from datetime import datetime

from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel

from agents.content_creator.tools.base_tool import ContentCreationTool
from agents.content_creator.tools.models import (
    FacebookTextLinkInput,
    FacebookImageInput,
    FacebookVideoInput,
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

# Meta Graph API configuration
META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


class MetaAPIClient:
    """Client for interacting with Meta Graph API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = None
    
    async def __aenter__(self):
        import aiohttp
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to Meta API"""
        data["access_token"] = self.access_token
        
        async with self.session.post(url, json=data) as response:
            result = await response.json()
            
            if response.status != 200:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"Meta API error: {error_msg}")
                raise Exception(f"Meta API error: {error_msg}")
            
            return result


class FacebookTextLinkPostTool(BaseTool, ContentCreationTool):
    """Tool for posting text with links to Facebook with validation"""
    
    name: str = "facebook_text_link_post"
    description: str = "Post text content with links to Facebook"
    args_schema: Type[BaseModel] = FacebookTextLinkInput
    
    def __init__(self, state: Optional[ContentGenerationState] = None):
        """Initialize with state tracker"""
        BaseTool.__init__(self)
        ContentCreationTool.__init__(self, state=state)
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        link_url: str,
        link_preview_title: Optional[str] = None,
        link_preview_description: Optional[str] = None,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Facebook text+link posting with validation"""
        try:
            logger.info(f"Facebook text+link post requested")
            
            # VALIDATION STEP: Check if we can create a Facebook post
            is_valid, error = self.validate_and_update_state("facebook_posts", 1)
            if not is_valid:
                logger.error(f"Post limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # Get Facebook tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Format message with hashtags
            hashtags = " ".join([f"#{tag}" for tag in tags])
            message = f"{caption}\n\n{hashtags}" if tags else caption
            
            async with MetaAPIClient(access_token) as client:
                url = f"{META_API_BASE}/{page_id}/feed"
                data = {
                    "message": message,
                    "link": link_url
                }
                
                # Note: Custom preview parameters are restricted by Meta
                # Facebook will generate the preview from the link's metadata
                
                result = await client.post(url, data)
                
                # Log remaining capacity
                if self.state:
                    remaining = self.state.get_remaining_capacity()
                    logger.info(f"Remaining capacity after post: {remaining}")
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    platform="facebook",
                    metadata={
                        "link": link_url,
                        "remaining_capacity": remaining if self.state else None
                    }
                )
                
        except Exception as e:
            logger.error(f"Facebook text+link post failed: {e}")
            
            # Rollback state on error
            if self.state:
                self.state.session_facebook_posts = max(0, self.state.session_facebook_posts - 1)
            
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="facebook",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


class FacebookImagePostTool(BaseTool, ContentCreationTool):
    """Tool for posting images to Facebook with validation"""
    
    name: str = "facebook_image_post"
    description: str = "Post single or album images to Facebook with AI-generated content"
    args_schema: Type[BaseModel] = FacebookImageInput
    
    def __init__(self, state: Optional[ContentGenerationState] = None):
        """Initialize with state tracker"""
        BaseTool.__init__(self)
        ContentCreationTool.__init__(self, state=state)
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        image_prompts: List[str],
        is_album: bool = False,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Facebook image posting with validation"""
        try:
            logger.info(f"Facebook image post requested: {len(image_prompts)} images")
            
            # VALIDATION STEP 1: Check if we can create a Facebook post
            is_valid, error = self.validate_and_update_state("facebook_posts", 1)
            if not is_valid:
                logger.error(f"Post limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
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
                    self.state.session_facebook_posts -= 1
                
                logger.error(f"Image limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # Get Facebook tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate images (validation already passed)
            logger.info("Generating images...")
            image_service = ImageGenerationService()
            
            # Pass execution tracking if available
            if hasattr(self, 'execution_id'):
                image_service.execution_id = self.execution_id
                image_service.execution_step = 'Content Creation'
            
            image_urls = await image_service.generate_images(
                prompts=image_prompts,
                initiative_id=initiative_id
            )
            
            if not image_urls:
                # Rollback state on failure
                if self.state:
                    self.state.session_facebook_posts -= 1
                    self.state.session_photos -= len(image_prompts)
                
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
                    error_message="Failed to generate images"
                )
            
            # Format caption
            hashtags = " ".join([f"#{tag}" for tag in tags])
            message = f"{caption}\n\n{hashtags}" if tags else caption
            
            async with MetaAPIClient(access_token) as client:
                if is_album and len(image_urls) > 1:
                    # Create album post
                    result = await self._create_album_post(
                        client, page_id, image_urls, message
                    )
                else:
                    # Create single image post
                    result = await self._create_single_image_post(
                        client, page_id, image_urls[0], message
                    )
                
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
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="facebook",
                    metadata={"remaining_capacity": remaining if self.state else None}
                )
                
        except Exception as e:
            logger.error(f"Facebook image post failed: {e}")
            
            # Rollback state on error
            if self.state:
                self.state.session_facebook_posts = max(0, self.state.session_facebook_posts - 1)
                self.state.session_photos = max(0, self.state.session_photos - len(image_prompts))
            
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="facebook",
                error_message=str(e)
            )
    
    async def _create_single_image_post(
        self,
        client: MetaAPIClient,
        page_id: str,
        image_url: str,
        caption: str
    ) -> Dict[str, Any]:
        """Create a single image post on Facebook"""
        url = f"{META_API_BASE}/{page_id}/photos"
        data = {
            "url": image_url,
            "caption": caption
        }
        
        return await client.post(url, data)
    
    async def _create_album_post(
        self,
        client: MetaAPIClient,
        page_id: str,
        image_urls: List[str],
        caption: str
    ) -> Dict[str, Any]:
        """Create an album post on Facebook"""
        # First, upload images without publishing
        photo_ids = []
        
        for i, image_url in enumerate(image_urls):
            url = f"{META_API_BASE}/{page_id}/photos"
            data = {
                "url": image_url,
                "published": False,
                "caption": caption if i == 0 else ""  # Caption only on first photo
            }
            
            result = await client.post(url, data)
            photo_ids.append(result["id"])
        
        # Create the album post with all photos
        url = f"{META_API_BASE}/{page_id}/feed"
        attached_media = [{"media_fbid": photo_id} for photo_id in photo_ids]
        data = {
            "message": caption,
            "attached_media": json.dumps(attached_media)
        }
        
        return await client.post(url, data)
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


class FacebookVideoPostTool(BaseTool, ContentCreationTool):
    """Tool for posting videos to Facebook with validation"""
    
    name: str = "facebook_video_post"
    description: str = "Post videos to Facebook with AI-generated content"
    args_schema: Type[BaseModel] = FacebookVideoInput
    
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
        video_title: Optional[str] = None,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Facebook video posting with validation"""
        try:
            logger.info("Facebook video post requested")
            
            # VALIDATION STEP 1: Check if we can create a Facebook post
            is_valid, error = self.validate_and_update_state("facebook_posts", 1)
            if not is_valid:
                logger.error(f"Post limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
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
                    self.state.session_facebook_posts -= 1
                
                logger.error(f"Video limit validation failed: {error}")
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
                    error_message=f"LIMIT EXCEEDED: {error}"
                )
            
            # Get Facebook tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate video (validation already passed)
            logger.info("Generating video...")
            video_service = VideoGenerationService()
            
            # Pass execution tracking if available
            if hasattr(self, 'execution_id'):
                video_service.execution_id = self.execution_id
                video_service.execution_step = 'Content Creation'
            
            video_url = await video_service.generate_video(
                prompt=video_prompt,
                initiative_id=initiative_id,
                duration_sec=duration_seconds
            )
            
            if not video_url:
                # Rollback state on failure
                if self.state:
                    self.state.session_facebook_posts -= 1
                    self.state.session_videos -= 1
                
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="facebook",
                    error_message="Failed to generate video"
                )
            
            # Format description
            hashtags = " ".join([f"#{tag}" for tag in tags])
            description = f"{caption}\n\n{hashtags}" if tags else caption
            
            async with MetaAPIClient(access_token) as client:
                # Upload video to Facebook
                url = f"{META_API_BASE}/{page_id}/videos"
                data = {
                    "file_url": video_url,
                    "description": description
                }
                
                if video_title:
                    data["title"] = video_title
                
                result = await client.post(url, data)
                
                # Create media file record
                media_files = [
                    MediaFile(
                        file_type=MediaType.VIDEO,
                        supabase_path=f"generated-media/{initiative_id}/videos/",
                        public_url=video_url,
                        prompt_used=video_prompt,
                        duration_seconds=duration_seconds
                    )
                ]
                
                # Log remaining capacity
                if self.state:
                    remaining = self.state.get_remaining_capacity()
                    logger.info(f"Remaining capacity after video: {remaining}")
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{page_id}/videos/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="facebook",
                    metadata={"remaining_capacity": remaining if self.state else None}
                )
                
        except Exception as e:
            logger.error(f"Facebook video post failed: {e}")
            
            # Rollback state on error
            if self.state:
                self.state.session_facebook_posts = max(0, self.state.session_facebook_posts - 1)
                self.state.session_videos = max(0, self.state.session_videos - 1)
            
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="facebook",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


# Export tool classes for use in ContentCreatorAgent
facebook_text_link_post_tool = FacebookTextLinkPostTool
facebook_image_post_tool = FacebookImagePostTool
facebook_video_post_tool = FacebookVideoPostTool