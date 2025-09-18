# agents/content_creator/tools/instagram_executor.py

"""
Instagram posting executor with deterministic execution.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import json

from agents.content_creator.tools.base_executor import BaseExecutor, PostingResult, PostingStatus
from backend.services.media_generation import ImageGenerationService, VideoGenerationService
from backend.services.token_manager import TokenManager
from agents.guardrails.state import ContentGenerationState
import logging
import aiohttp

logger = logging.getLogger(__name__)

META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.instagram.com/{META_API_VERSION}"


class InstagramExecutor(BaseExecutor):
    """Executes Instagram posting operations deterministically"""
    
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
        """Execute Instagram posting based on post type"""
        post_type = post_data.get("post_type", "").lower()
        
        if post_type in ["image", "carousel"]:
            return await self._execute_image_post(post_data)
        elif post_type in ["video", "reel"]:
            return await self._execute_reel_post(post_data)
        elif post_type == "story":
            return await self._execute_story_post(post_data)
        else:
            return PostingResult(
                success=False,
                error_message=f"Unsupported post type for Instagram: {post_type}",
                status=PostingStatus.FAILED
            )
    
    async def _execute_image_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute image/carousel posting"""
        start_time = time.time()
        
        post_id = post_data.get("post_id")
        content = post_data.get("content", {})
        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        media_specs = post_data.get("media", [])
        
        self._log_start("Instagram Image Post", {
            "post_id": post_id,
            "media_count": len(media_specs),
            "type": "carousel" if len(media_specs) > 1 else "single"
        })
        
        try:
            # Get Instagram tokens
            tokens = await self.token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate images
            logger.info(f"📸 Generating {len(media_specs)} images for Instagram...")
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
            
            # Create Instagram media container(s)
            logger.info("📤 Creating Instagram media containers...")
            async with aiohttp.ClientSession() as session:
                if len(image_urls) > 1:
                    ig_result = await self._create_carousel(
                        session, ig_user_id, access_token, image_urls, full_caption
                    )
                else:
                    ig_result = await self._create_single_image(
                        session, ig_user_id, access_token, image_urls[0], full_caption
                    )
            
            execution_time = time.time() - start_time
            
            self._log_end("Instagram Image Post", True, {
                "instagram_id": ig_result.get("id"),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=ig_result.get("id"),
                platform_url=f"https://www.instagram.com/p/{ig_result.get('id')}/",
                platform="instagram",
                status=PostingStatus.PUBLISHED,
                media_urls=image_urls,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Instagram image post failed: {e}")
            
            self._log_end("Instagram Image Post", False, {
                "error": str(e),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="instagram",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _execute_reel_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute Reel posting with polling"""
        start_time = time.time()
        
        post_id = post_data.get("post_id")
        content = post_data.get("content", {})
        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        media_specs = post_data.get("media", [])
        
        if not media_specs:
            return PostingResult(
                success=False,
                post_id=post_id,
                error_message="No video media specified for Reel",
                status=PostingStatus.FAILED
            )
        
        video_spec = media_specs[0]
        duration = video_spec.get("duration_seconds", 15)
        
        self._log_start("Instagram Reel Post", {
            "post_id": post_id,
            "duration": f"{duration}s"
        })
        
        try:
            # Get tokens
            tokens = await self.token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate video
            logger.info(f"🎬 Generating Reel video (duration: {duration}s)...")
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
                        logger.info(f"✅ Reel video generated successfully after {poll_count * 5}s")
                        break
                    else:
                        raise Exception("Reel video generation failed")
                
                poll_count += 1
                logger.info(f"⏳ Reel generation in progress... (poll {poll_count}/{max_polls})")
                await asyncio.sleep(5)
            
            if poll_count >= max_polls:
                generation_task.cancel()
                raise Exception("Reel generation timeout after 5 minutes")
            
            # Format caption
            hashtag_text = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_text}" if hashtags else caption
            
            # Create Reel on Instagram
            logger.info("📤 Publishing Reel to Instagram...")
            async with aiohttp.ClientSession() as session:
                ig_result = await self._create_reel(
                    session, ig_user_id, access_token, video_url, full_caption
                )
            
            execution_time = time.time() - start_time
            
            self._log_end("Instagram Reel Post", True, {
                "instagram_id": ig_result.get("id"),
                "generation_time": f"{poll_count * 5}s",
                "total_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=ig_result.get("id"),
                platform_url=f"https://www.instagram.com/reel/{ig_result.get('id')}/",
                platform="instagram",
                status=PostingStatus.PUBLISHED,
                media_urls=[video_url],
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Instagram Reel post failed: {e}")
            
            self._log_end("Instagram Reel Post", False, {
                "error": str(e),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="instagram",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _execute_story_post(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute Story posting"""
        start_time = time.time()
        post_id = post_data.get("post_id")
        media_specs = post_data.get("media", [])
        
        self._log_start("Instagram Story Post", {"post_id": post_id})
        
        try:
            # Get tokens
            tokens = await self.token_manager.get_instagram_tokens()
            ig_user_id = tokens["business_id"]
            access_token = tokens["access_token"]
            
            # Generate story media (image or short video)
            if media_specs and media_specs[0].get("format") in ["mp4", "mov"]:
                # Video story
                video_service = VideoGenerationService()
                if self.execution_id:
                    video_service.execution_id = self.execution_id
                    video_service.execution_step = self.execution_step
                
                media_url = await video_service.generate_video(
                    prompt=media_specs[0].get("url", ""),
                    initiative_id=self.initiative_id,
                    duration_sec=15  # Stories are max 15 seconds
                )
            else:
                # Image story
                image_service = ImageGenerationService()
                if self.execution_id:
                    image_service.execution_id = self.execution_id
                    image_service.execution_step = self.execution_step
                
                urls = await image_service.generate_images(
                    prompts=[media_specs[0].get("url", "")] if media_specs else [""],
                    initiative_id=self.initiative_id
                )
                media_url = urls[0] if urls else None
            
            if not media_url:
                raise Exception("Failed to generate story media")
            
            # Create story
            async with aiohttp.ClientSession() as session:
                ig_result = await self._create_story(
                    session, ig_user_id, access_token, media_url
                )
            
            execution_time = time.time() - start_time
            
            self._log_end("Instagram Story Post", True, {
                "instagram_id": ig_result.get("id"),
                "execution_time": f"{execution_time:.2f}s"
            })
            
            return PostingResult(
                success=True,
                post_id=post_id,
                platform_post_id=ig_result.get("id"),
                platform_url=f"https://www.instagram.com/stories/",
                platform="instagram",
                status=PostingStatus.PUBLISHED,
                media_urls=[media_url],
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._log_end("Instagram Story Post", False, {"error": str(e)})
            
            return PostingResult(
                success=False,
                post_id=post_id,
                platform="instagram",
                status=PostingStatus.FAILED,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _create_single_image(
        self, session: aiohttp.ClientSession, ig_user_id: str,
        access_token: str, image_url: str, caption: str
    ) -> Dict[str, Any]:
        """Create single image post"""
        
        # Debug: Log token details
        logger.debug(f"Instagram API Call - _create_single_image")
        logger.debug(f"  IG User ID: {ig_user_id}")
        logger.debug(f"  Token length: {len(access_token)}")
        logger.debug(f"  Token preview: {access_token[:30]}...{access_token[-10:]}")
        logger.debug(f"  Token starts with 'IG': {access_token.startswith('IG')}")
        logger.debug(f"  Image URL: {image_url}")
        logger.debug(f"  Caption length: {len(caption)}")
        
        # Create media container
        url = f"{META_API_BASE}/{ig_user_id}/media"
        json_data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,  # Include token in JSON body, not params
        }
        
        headers = {
            "Content-Type": "application/json"  # Explicitly set like curl
        }
        
        async with session.post(url, json=json_data, headers=headers) as response:
            result = await response.json()
            if response.status != 200:
                logger.error(f"Instagram API Error: {result}")
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            container_id = result["id"]
        
        # Publish the container - ALSO use JSON format
        url = f"{META_API_BASE}/{ig_user_id}/media_publish"
        json_data = {
            "creation_id": container_id,
            "access_token": access_token  # In JSON body
        }
        
        async with session.post(url, json=json_data, headers=headers) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result
    
    # async def _create_single_image(
    #     self, session: aiohttp.ClientSession, ig_user_id: str,
    #     access_token: str, image_url: str, caption: str
    # ) -> Dict[str, Any]:
    #     """Create single image post"""
    #     # Create media container
    #     url = f"{META_API_BASE}/{ig_user_id}/media"
    #     params = {
    #         "access_token": access_token
    #     }
    #     data = {
    #         "image_url": image_url,
    #         "caption": caption
    #     }
        
    #     async with session.post(url, params=params, data=data) as response:
    #         result = await response.json()
    #         if response.status != 200:
    #             raise Exception(result.get("error", {}).get("message", "Unknown error"))
    #         container_id = result["id"]
        
    #     # Publish the container
    #     url = f"{META_API_BASE}/{ig_user_id}/media_publish"
    #     data = {
    #         "creation_id": container_id,
    #         "access_token": access_token
    #     }
        
    #     async with session.post(url, params=params, data=data) as response:
    #         result = await response.json()
    #         if response.status != 200:
    #             raise Exception(result.get("error", {}).get("message", "Unknown error"))
    #         return result
    
    async def _create_carousel(
        self, session: aiohttp.ClientSession, ig_user_id: str,
        access_token: str, image_urls: List[str], caption: str
    ) -> Dict[str, Any]:
        """Create carousel post"""
        # Create containers for each image
        container_ids = []
        
        for image_url in image_urls:
            url = f"{META_API_BASE}/{ig_user_id}/media"
            data = {
                "image_url": image_url,
                "is_carousel_item": True,
                "access_token": access_token
            }
            
            async with session.post(url, data=data) as response:
                result = await response.json()
                if response.status != 200:
                    raise Exception(result.get("error", {}).get("message", "Unknown error"))
                container_ids.append(result["id"])
        
        # Create carousel container
        url = f"{META_API_BASE}/{ig_user_id}/media"
        data = {
            "media_type": "CAROUSEL",
            "children": ",".join(container_ids),
            "caption": caption,
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            carousel_id = result["id"]
        
        # Publish carousel
        url = f"{META_API_BASE}/{ig_user_id}/media_publish"
        data = {
            "creation_id": carousel_id,
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result
    
    async def _create_reel(
        self, session: aiohttp.ClientSession, ig_user_id: str,
        access_token: str, video_url: str, caption: str
    ) -> Dict[str, Any]:
        """Create Reel post"""
        
        # Create Reel container using JSON format
        url = f"{META_API_BASE}/{ig_user_id}/media"
        json_data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token
        }
        headers = {"Content-Type": "application/json"}
        
        async with session.post(url, json=json_data, headers=headers) as response:
            result = await response.json()
            if response.status != 200:
                logger.error(f"Instagram API Error: {result}")
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            container_id = result["id"]
        
        # Poll for upload status
        logger.info(f"⏳ Waiting for Reel upload to complete...")
        max_polls = 60  # 5 minutes max
        poll_interval = 5  # seconds
        
        for poll_count in range(1, max_polls + 1):
            # Check status
            status_url = f"{META_API_BASE}/{container_id}"
            params = {
                "fields": "status_code",
                "access_token": access_token
            }
            
            async with session.get(status_url, params=params) as response:
                status_result = await response.json()
                status_code = status_result.get("status_code")
                
                logger.info(f"Upload status: {status_code} (poll {poll_count}/{max_polls})")
                
                if status_code == "FINISHED":
                    logger.info("✅ Reel upload finished, publishing...")
                    break
                elif status_code == "ERROR":
                    raise Exception(f"Reel upload failed with ERROR status")
                
                if poll_count >= max_polls:
                    raise Exception("Reel upload timeout after 5 minutes")
                
                await asyncio.sleep(poll_interval)
        
        # Publish Reel using JSON format
        url = f"{META_API_BASE}/{ig_user_id}/media_publish"
        json_data = {
            "creation_id": container_id,
            "access_token": access_token
        }
        
        async with session.post(url, json=json_data, headers=headers) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result
    
    async def _create_story(
        self, session: aiohttp.ClientSession, ig_user_id: str,
        access_token: str, media_url: str
    ) -> Dict[str, Any]:
        """Create Story post"""
        # Stories API endpoint
        url = f"{META_API_BASE}/{ig_user_id}/media"
        data = {
            "media_type": "STORIES",
            "image_url": media_url,  # or video_url for video stories
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            container_id = result["id"]
        
        # Publish story
        url = f"{META_API_BASE}/{ig_user_id}/media_publish"
        data = {
            "creation_id": container_id,
            "access_token": access_token
        }
        
        async with session.post(url, data=data) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(result.get("error", {}).get("message", "Unknown error"))
            return result