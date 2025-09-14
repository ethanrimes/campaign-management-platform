"""
LangChain tools for posting to Instagram and Facebook via Meta Graph API.
Integrates with Gemini AI for media generation and Supabase for storage.
"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import aiohttp

from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from agents.content_creator.tools.models import (
    InstagramImageInput,
    InstagramReelInput,
    FacebookTextLinkInput,
    FacebookImageInput,
    FacebookVideoInput,
    PostResponse,
    PostStatus,
    MediaFile,
    MediaType
)
from backend.services.media_generation import (
    ImageGenerationService,
    VideoGenerationService
)
from backend.services.token_manager import TokenManager
from backend.db.supabase_client import DatabaseClient

logger = logging.getLogger(__name__)

# Meta Graph API configuration
META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"
INSTAGRAM_API_BASE = f"https://graph.instagram.com/{META_API_VERSION}"


class MetaAPIClient:
    """Client for interacting with Meta Graph API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = None
    
    async def __aenter__(self):
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
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to Meta API"""
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        async with self.session.get(url, params=params) as response:
            result = await response.json()
            
            if response.status != 200:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"Meta API error: {error_msg}")
                raise Exception(f"Meta API error: {error_msg}")
            
            return result


class InstagramImagePostTool(BaseTool):
    """Tool for posting images to Instagram"""
    
    name: str = "instagram_image_post"
    description: str = "Post single or carousel images to Instagram with AI-generated content"
    args_schema: Type[BaseModel] = InstagramImageInput
    
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
        """Execute Instagram image posting"""
        try:
            # Get Instagram tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate images
            image_service = ImageGenerationService()
            image_urls = await image_service.generate_images(
                prompts=image_prompts,
                initiative_id=initiative_id,
                num_per_prompt=1
            )
            
            if not image_urls:
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message="Failed to generate images"
                )
            
            # Format caption with hashtags
            full_caption = self._format_caption(caption, tags)
            
            async with MetaAPIClient(access_token) as client:
                if is_carousel and len(image_urls) > 1:
                    # Create carousel post
                    container_id = await self._create_carousel_container(
                        client, ig_user_id, image_urls, full_caption
                    )
                else:
                    # Create single image post
                    container_id = await self._create_image_container(
                        client, ig_user_id, image_urls[0], full_caption
                    )
                
                # Publish the container
                result = await self._publish_container(client, ig_user_id, container_id)
                
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
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.instagram.com/p/{result.get('id')}/",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="instagram",
                    container_id=container_id
                )
                
        except Exception as e:
            logger.error(f"Instagram image post failed: {e}")
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="instagram",
                error_message=str(e)
            )
    
    async def _create_image_container(
        self,
        client: MetaAPIClient,
        ig_user_id: str,
        image_url: str,
        caption: str
    ) -> str:
        """Create an Instagram media container for a single image"""
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
        data = {
            "image_url": image_url,
            "caption": caption
        }
        
        result = await client.post(url, data)
        return result["id"]
    
    async def _create_carousel_container(
        self,
        client: MetaAPIClient,
        ig_user_id: str,
        image_urls: List[str],
        caption: str
    ) -> str:
        """Create an Instagram carousel container"""
        # First, create individual media containers for each image
        child_containers = []
        
        for image_url in image_urls:
            url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
            data = {
                "image_url": image_url,
                "is_carousel_item": True
            }
            result = await client.post(url, data)
            child_containers.append(result["id"])
        
        # Create the carousel container
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
        data = {
            "media_type": "CAROUSEL",
            "children": child_containers,
            "caption": caption
        }
        
        result = await client.post(url, data)
        return result["id"]
    
    async def _publish_container(
        self,
        client: MetaAPIClient,
        ig_user_id: str,
        container_id: str
    ) -> Dict[str, Any]:
        """Publish an Instagram media container"""
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media_publish"
        data = {"creation_id": container_id}
        
        return await client.post(url, data)
    
    def _format_caption(self, caption: str, tags: List[str]) -> str:
        """Format caption with hashtags"""
        hashtags = " ".join([f"#{tag}" for tag in tags])
        return f"{caption}\n\n{hashtags}" if tags else caption
    
    def _run(self, *args, **kwargs):
        """Synchronous run method (required by BaseTool)"""
        return asyncio.run(self._arun(*args, **kwargs))


class InstagramReelPostTool(BaseTool):
    """Tool for posting Reels to Instagram"""
    
    name: str = "instagram_reel_post"
    description: str = "Post video Reels to Instagram with AI-generated content"
    args_schema: Type[BaseModel] = InstagramReelInput
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        video_prompt: str,
        duration_seconds: int = 15,
        cover_image_prompt: Optional[str] = None,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Instagram Reel posting"""
        try:
            # Get Instagram tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate video
            video_service = VideoGenerationService()
            video_url = await video_service.generate_video(
                prompt=video_prompt,
                initiative_id=initiative_id,
                duration_sec=duration_seconds
            )
            
            if not video_url:
                return PostResponse(
                    success=False,
                    status=PostStatus.FAILED,
                    platform="instagram",
                    error_message="Failed to generate video"
                )
            
            # Generate cover image if requested
            cover_url = None
            if cover_image_prompt:
                image_service = ImageGenerationService()
                cover_urls = await image_service.generate_images(
                    prompts=[cover_image_prompt],
                    initiative_id=initiative_id
                )
                cover_url = cover_urls[0] if cover_urls else None
            
            # Format caption
            full_caption = self._format_caption(caption, tags)
            
            async with MetaAPIClient(access_token) as client:
                # Create Reel container
                container_id = await self._create_reel_container(
                    client, ig_user_id, video_url, full_caption, cover_url
                )
                
                # Wait for video processing
                await self._wait_for_container(client, container_id)
                
                # Publish the Reel
                result = await self._publish_container(client, ig_user_id, container_id)
                
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
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.instagram.com/reel/{result.get('id')}/",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="instagram",
                    container_id=container_id
                )
                
        except Exception as e:
            logger.error(f"Instagram Reel post failed: {e}")
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="instagram",
                error_message=str(e)
            )
    
    async def _create_reel_container(
        self,
        client: MetaAPIClient,
        ig_user_id: str,
        video_url: str,
        caption: str,
        cover_url: Optional[str] = None
    ) -> str:
        """Create an Instagram Reel container"""
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
        data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption
        }
        
        if cover_url:
            data["cover_url"] = cover_url
        
        result = await client.post(url, data)
        return result["id"]
    
    async def _wait_for_container(
        self,
        client: MetaAPIClient,
        container_id: str,
        max_attempts: int = 30
    ):
        """Wait for video container to be processed"""
        url = f"{INSTAGRAM_API_BASE}/{container_id}"
        
        for attempt in range(max_attempts):
            result = await client.get(url, {"fields": "status_code"})
            status = result.get("status_code")
            
            if status == "FINISHED":
                return
            elif status == "ERROR":
                raise Exception("Video processing failed")
            
            # Wait before next check
            await asyncio.sleep(2)
        
        raise Exception("Video processing timeout")
    
    async def _publish_container(
        self,
        client: MetaAPIClient,
        ig_user_id: str,
        container_id: str
    ) -> Dict[str, Any]:
        """Publish an Instagram media container"""
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media_publish"
        data = {"creation_id": container_id}
        
        return await client.post(url, data)
    
    def _format_caption(self, caption: str, tags: List[str]) -> str:
        """Format caption with hashtags"""
        hashtags = " ".join([f"#{tag}" for tag in tags])
        return f"{caption}\n\n{hashtags}" if tags else caption
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


class FacebookTextLinkPostTool(BaseTool):
    """Tool for posting text with links to Facebook"""
    
    name: str = "facebook_text_link_post"
    description: str = "Post text content with links to Facebook"
    args_schema: Type[BaseModel] = FacebookTextLinkInput
    
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
        """Execute Facebook text+link posting"""
        try:
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
                
                # Add custom preview if provided
                if link_preview_title:
                    data["name"] = link_preview_title
                if link_preview_description:
                    data["description"] = link_preview_description
                
                result = await client.post(url, data)
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    platform="facebook",
                    metadata={"link": link_url}
                )
                
        except Exception as e:
            logger.error(f"Facebook text+link post failed: {e}")
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="facebook",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


class FacebookImagePostTool(BaseTool):
    """Tool for posting images to Facebook"""
    
    name: str = "facebook_image_post"
    description: str = "Post single or album images to Facebook with AI-generated content"
    args_schema: Type[BaseModel] = FacebookImageInput
    
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
        """Execute Facebook image posting"""
        try:
            # Get Facebook tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate images
            image_service = ImageGenerationService()
            image_urls = await image_service.generate_images(
                prompts=image_prompts,
                initiative_id=initiative_id
            )
            
            if not image_urls:
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
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="facebook"
                )
                
        except Exception as e:
            logger.error(f"Facebook image post failed: {e}")
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


class FacebookVideoPostTool(BaseTool):
    """Tool for posting videos to Facebook"""
    
    name: str = "facebook_video_post"
    description: str = "Post videos to Facebook with AI-generated content"
    args_schema: Type[BaseModel] = FacebookVideoInput
    
    async def _arun(
        self,
        initiative_id: str,
        caption: str,
        tags: List[str],
        video_prompt: str,
        duration_seconds: int = 30,
        video_title: Optional[str] = None,
        metadata: Dict[str, Any] = {},
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> PostResponse:
        """Execute Facebook video posting"""
        try:
            # Get Facebook tokens
            token_manager = TokenManager(initiative_id)
            tokens = await token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate video
            video_service = VideoGenerationService()
            video_url = await video_service.generate_video(
                prompt=video_prompt,
                initiative_id=initiative_id,
                duration_sec=duration_seconds
            )
            
            if not video_url:
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
                
                return PostResponse(
                    success=True,
                    post_id=result.get("id"),
                    post_url=f"https://www.facebook.com/{page_id}/videos/{result.get('id')}",
                    status=PostStatus.PUBLISHED,
                    media_files=media_files,
                    platform="facebook"
                )
                
        except Exception as e:
            logger.error(f"Facebook video post failed: {e}")
            return PostResponse(
                success=False,
                status=PostStatus.FAILED,
                platform="facebook",
                error_message=str(e)
            )
    
    def _run(self, *args, **kwargs):
        """Synchronous run method"""
        return asyncio.run(self._arun(*args, **kwargs))


# Export tools for easy import
instagram_image_post_tool = InstagramImagePostTool()
instagram_reel_post_tool = InstagramReelPostTool()
facebook_text_link_post_tool = FacebookTextLinkPostTool()
facebook_image_post_tool = FacebookImagePostTool()
facebook_video_post_tool = FacebookVideoPostTool()