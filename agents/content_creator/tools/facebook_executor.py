# agents/content_creator/tools/facebook_executor.py

"""
Facebook posting executor with deterministic execution.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.content_creator.tools.base_executor import BaseExecutor, PostingResult, PostingStatus
from backend.services.media_generation import ImageGenerationService, VideoGenerationService
from backend.services.token_manager import TokenManager
from agents.guardrails.state import ContentGenerationState
import logging
import aiohttp
import json

logger = logging.getLogger(__name__)

META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


class FacebookExecutor(BaseExecutor):
    """Executes Facebook posting operations deterministically"""
    
    def __init__(
        self, 
        initiative_id: str,
        state: Optional[ContentGenerationState] = None,
        execution_id: Optional[str] = None
    ):
        super().__init__(initiative_id, execution_id)
        self.state = state
        self.token_manager = TokenManager(initiative_id)
    
    async def execute(self, post_data: Dict[str, Any]) -> PostingResult:
        """
        Execute Facebook posting based on post type.
        
        Args:
            post_data: Post data from ContentBatch
            
        Returns:
            PostingResult with platform-specific IDs
        """
        post_type = post_data.get("post_type", "").lower()
        
        # Route to appropriate method based on post type
        if post_type in ["image", "carousel"]:
            return await self._execute_image_post(post_data)
        elif post_type == "video":
            return await self._execute_video_post(post_data)
        elif post_type in ["text", "link"]:
            return await self._execute_text_post(post_data)
        else:
            return PostingResult(
                success=False,
                error_message=f"Unsupported post type for Facebook: {post_type}",
                status=PostingStatus.FAILED
            )
    
    async def _execute_image_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute image/carousel posting"""
        start_time = time.time()
        
        # Extract data
        post_id = post_data.get("post_id")
        content = post_data.get("content", {})
        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        media_specs = post_data.get("media", [])
        
        self._log_start("Facebook Image Post", {
            "post_id": post_id,
            "media_count": len(media_specs),
            "type": "carousel" if len(media_specs) > 1 else "single"
        })
        
        try:
            # Get Facebook tokens
            tokens = await self.token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate images
            logger.info(f"📸 Generating {len(media_specs)} images...")
            image_service = ImageGenerationService()
            if self.execution_id:
                image_service.execution_id = self.execution_id
                image_service.execution_step = self.execution_step
            
            image_prompts = [spec.get("url", "") for spec in media_specs]
            image_urls = await image_service.generate_images(
                prompts=image_prompts,
                initiative_id=self.initiative_id
            )
            
            if not image_urls:
                raise Exception("Failed to generate images")
            
            logger.info(f"✅ Generated {len(image_urls)} images successfully")
            
            # Format caption with hashtags
            hashtag_text = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_text}" if hashtags else caption
            
            # Post to Facebook
            logger.info("📤 Posting to Facebook...")
            async with aiohttp.ClientSession() as session:
                if len(image_urls) > 1:
                    # Create album post
                    fb_result = await self._create_album(
                        session, page_id, access_token, image_urls, full_caption
                    )
                else:
                    # Single image post
                    fb_result = await self._create_single_image(
                        session, page_id, access_token, image_urls[0], full_caption
                    )
            
            execution_time = time.time() - start_time
            
            self._log_end("Facebook Image Post", True, {
                "facebook_id": fb_result.get("id"),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=fb_result.get("id"),
                platform_url=f"https://www.facebook.com/{fb_result.get('id')}",
                platform="facebook",
                status=PostingStatus.PUBLISHED,
                media_urls=image_urls,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Facebook image post failed: {e}")
            
            self._log_end("Facebook Image Post", False, {
                "error": str(e),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="facebook",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _execute_video_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute video posting with polling"""
        start_time = time.time()
        
        # Extract data
        post_id = post_data.get("post_id")
        content = post_data.get("content", {})
        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        media_specs = post_data.get("media", [])
        
        if not media_specs:
            return PostingResult(
                success=False,
                post_id=post_id,
                error_message="No video media specified",
                status=PostingStatus.FAILED
            )
        
        video_spec = media_specs[0]  # Use first video
        duration = video_spec.get("duration_seconds", 30)
        
        self._log_start("Facebook Video Post", {
            "post_id": post_id,
            "duration": f"{duration}s"
        })
        
        try:
            # Get tokens
            tokens = await self.token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Generate video
            logger.info(f"🎬 Generating video (duration: {duration}s)...")
            video_service = VideoGenerationService()
            if self.execution_id:
                video_service.execution_id = self.execution_id
                video_service.execution_step = self.execution_step
            
            video_prompt = video_spec.get("url", "")
            
            # Start video generation
            generation_task = asyncio.create_task(
                video_service.generate_video(
                    prompt=video_prompt,
                    initiative_id=self.initiative_id,
                    duration_sec=duration
                )
            )
            
            # Poll for status every 5 seconds
            poll_count = 0
            max_polls = 60  # 5 minutes max
            
            while poll_count < max_polls:
                if generation_task.done():
                    video_url = await generation_task
                    if video_url:
                        logger.info(f"✅ Video generated successfully after {poll_count * 5}s")
                        break
                    else:
                        raise Exception("Video generation failed")
                
                poll_count += 1
                logger.info(f"⏳ Video generation in progress... (poll {poll_count}/{max_polls})")
                await asyncio.sleep(5)
            
            if poll_count >= max_polls:
                generation_task.cancel()
                raise Exception("Video generation timeout after 5 minutes")
            
            # Format caption
            hashtag_text = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_text}" if hashtags else caption
            
            # Upload to Facebook
            logger.info("📤 Uploading video to Facebook...")
            async with aiohttp.ClientSession() as session:
                fb_result = await self._upload_video(
                    session, page_id, access_token, video_url, full_caption
                )
            
            execution_time = time.time() - start_time
            
            self._log_end("Facebook Video Post", True, {
                "facebook_id": fb_result.get("id"),
                "generation_time": f"{poll_count * 5}s",
                "total_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=fb_result.get("id"),
                platform_url=f"https://www.facebook.com/{page_id}/videos/{fb_result.get('id')}",
                platform="facebook",
                status=PostingStatus.PUBLISHED,
                media_urls=[video_url],
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Facebook video post failed: {e}")
            
            self._log_end("Facebook Video Post", False, {
                "error": str(e),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="facebook",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _execute_text_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute text/link posting"""
        start_time = time.time()
        post_id = post_data.get("post_id")
        content = post_data.get("content", {})
        
        self._log_start("Facebook Text Post", {"post_id": post_id})
        
        try:
            tokens = await self.token_manager.get_facebook_tokens()
            page_id = tokens["page_id"]
            access_token = tokens["page_access_token"]
            
            # Format message
            caption = content.get("caption", "")
            hashtags = content.get("hashtags", [])
            links = content.get("links", [])
            
            hashtag_text = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags])
            message = f"{caption}\n\n{hashtag_text}" if hashtags else caption
            
            # Post to Facebook
            async with aiohttp.ClientSession() as session:
                url = f"{META_API_BASE}/{page_id}/feed"
                data = {
                    "message": message,
                    "access_token": access_token
                }
                
                if links:
                    data["link"] = links[0]
                
                async with session.post(url, data=data) as response:
                    fb_result = await response.json()
                    
                    if response.status != 200:
                        raise Exception(fb_result.get("error", {}).get("message", "Unknown error"))
            
            execution_time = time.time() - start_time
            
            self._log_end("Facebook Text Post", True, {
                "facebook_id": fb_result.get("id"),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=fb_result.get("id"),
                platform_url=f"https://www.facebook.com/{fb_result.get('id')}",
                platform="facebook",
                status=PostingStatus.PUBLISHED,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._log_end("Facebook Text Post", False, {"error": str(e)})
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="facebook",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _create_single_image(
        self, session: aiohttp.ClientSession, page_id: str, 
        access_token: str, image_url: str, caption: str
    ) -> Dict[str, Any]:
        """Create single image post"""
        url = f"{META_API_BASE}/{page_id}/photos"
        data = {
            "url": image_url,
            "caption": caption,
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result
    
    async def _create_album(
        self, session: aiohttp.ClientSession, page_id: str,
        access_token: str, image_urls: List[str], caption: str
    ) -> Dict[str, Any]:
        """Create album post with multiple images"""
        # Upload images without publishing
        photo_ids = []
        
        for i, image_url in enumerate(image_urls):
            url = f"{META_API_BASE}/{page_id}/photos"
            data = {
                "url": image_url,
                "published": False,
                "caption": caption if i == 0 else "",
                "access_token": access_token
            }
            
            async with session.post(url, data=data) as response:
                result = await response.json()
                if response.status != 200:
                    raise Exception(result.get("error", {}).get("message", "Unknown error"))
                photo_ids.append(result["id"])
        
        # Create album post
        url = f"{META_API_BASE}/{page_id}/feed"
        attached_media = [{"media_fbid": pid} for pid in photo_ids]
        data = {
            "message": caption,
            "attached_media": json.dumps(attached_media),
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result
    
    async def _upload_video(
        self, session: aiohttp.ClientSession, page_id: str,
        access_token: str, video_url: str, description: str
    ) -> Dict[str, Any]:
        """Upload video to Facebook"""
        url = f"{META_API_BASE}/{page_id}/videos"
        data = {
            "file_url": video_url,
            "description": description,
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result