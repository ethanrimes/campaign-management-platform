# backend/services/media_generation.py

"""
Media generation services using Wavespeed AI APIs.
Handles image generation with SDXL-LoRA and video generation with WAN-2.2.
Enhanced with detailed debug logging for troubleshooting.
"""

import asyncio
import logging
import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4
import aiohttp
import base64
from pathlib import Path

from backend.config.settings import settings
from backend.db.supabase_client import DatabaseClient
from supabase import create_client, Client as SupabaseClient

logger = logging.getLogger(__name__)


class MediaGenerationService:
    """Base class for media generation services"""
    
    def __init__(self):
        self.api_key = settings.WAVESPEED_API_KEY
        if not self.api_key:
            raise ValueError("WAVESPEED_API_KEY not found in settings")
        
        self.api_base = settings.WAVESPEED_API_BASE
        self.polling_interval = settings.WAVESPEED_POLLING_INTERVAL
        self.max_poll_attempts = settings.WAVESPEED_MAX_POLL_ATTEMPTS
        
        logger.debug(f"MediaGenerationService initialized:")
        logger.debug(f"  API Base: {self.api_base}")
        logger.debug(f"  Polling Interval: {self.polling_interval}s")
        logger.debug(f"  Max Poll Attempts: {self.max_poll_attempts}")
        
        # Initialize Supabase client with SERVICE KEY for storage operations
        self.supabase: SupabaseClient = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        logger.debug(f"  Supabase URL: {settings.SUPABASE_URL}")
    
    async def _submit_task(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> str:
        """Submit a generation task and return the request ID"""
        url = f"{self.api_base}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.debug(f"Submitting task to: {url}")
        logger.debug(f"Payload: {payload}")
        
        start_time = time.time()
        async with session.post(url, headers=headers, json=payload) as response:
            elapsed = time.time() - start_time
            logger.debug(f"API response received in {elapsed:.2f}s - Status: {response.status}")
            
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Wavespeed API error ({response.status}): {error_text}")
                raise Exception(f"Task submission failed: {error_text}")
            
            result = await response.json()
            request_id = result["data"]["id"]
            logger.info(f"✅ Task submitted successfully. Request ID: {request_id}")
            logger.debug(f"Full response: {result}")
            return request_id
    
    async def _poll_for_result(
        self,
        session: aiohttp.ClientSession,
        request_id: str
    ) -> Optional[str]:
        """Poll for task completion and return the result URL"""
        url = f"{self.api_base}/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        logger.debug(f"Starting to poll for result: {request_id}")
        start_time = time.time()
        
        for attempt in range(self.max_poll_attempts):
            poll_start = time.time()
            async with session.get(url, headers=headers) as response:
                poll_elapsed = time.time() - poll_start
                logger.debug(f"Poll attempt {attempt + 1}/{self.max_poll_attempts} - Response in {poll_elapsed:.2f}s")
                
                if response.status != 200:
                    logger.warning(f"Poll attempt {attempt + 1} failed: HTTP {response.status}")
                    await asyncio.sleep(self.polling_interval)
                    continue
                
                result = await response.json()
                status = result["data"]["status"]
                logger.debug(f"Task status: {status}")
                
                if status == "completed":
                    total_elapsed = time.time() - start_time
                    outputs = result["data"]["outputs"]
                    logger.info(f"✅ Task completed in {total_elapsed:.2f}s")
                    logger.debug(f"Outputs: {outputs}")
                    
                    if outputs and len(outputs) > 0:
                        output_url = outputs[0]
                        logger.info(f"Output URL: {output_url}")
                        return output_url
                    else:
                        logger.error("Task completed but no output URL returned")
                        logger.debug(f"Full result: {result}")
                        raise Exception("Task completed but no output URL returned")
                        
                elif status == "failed":
                    error = result["data"].get("error", "Unknown error")
                    logger.error(f"Task failed: {error}")
                    logger.debug(f"Full result: {result}")
                    raise Exception(f"Task failed: {error}")
                else:
                    logger.debug(f"Task still {status}, waiting {self.polling_interval}s...")
            
            await asyncio.sleep(self.polling_interval)
        
        total_elapsed = time.time() - start_time
        logger.error(f"Task timed out after {self.max_poll_attempts} attempts ({total_elapsed:.2f}s)")
        raise Exception(f"Task timed out after {self.max_poll_attempts} attempts")
    
    async def _download_media(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> bytes:
        """Download media from URL"""
        logger.debug(f"Downloading media from: {url}")
        start_time = time.time()
        
        try:
            async with session.get(url) as response:
                elapsed = time.time() - start_time
                logger.debug(f"Download response received in {elapsed:.2f}s - Status: {response.status}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to download media: HTTP {response.status}")
                    logger.error(f"Error response: {error_text}")
                    raise Exception(f"Failed to download media from {url}: HTTP {response.status}")
                
                content = await response.read()
                content_size = len(content)
                logger.info(f"✅ Downloaded {content_size:,} bytes in {elapsed:.2f}s")
                logger.debug(f"Content type: {response.headers.get('Content-Type')}")
                
                return content
                
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for URL: {url}")
            raise Exception(f"Download timeout for URL: {url}")
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    async def _upload_to_supabase(
        self,
        file_bytes: bytes,
        initiative_id: UUID,
        media_type: str,
        file_extension: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload file to Supabase storage and return public URL"""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_id = uuid4().hex[:8]
            filename = f"{timestamp}_{file_id}.{file_extension}"
            
            storage_path = f"{initiative_id}/{media_type}/{filename}"
            
            logger.debug(f"Uploading to Supabase:")
            logger.debug(f"  Path: {storage_path}")
            logger.debug(f"  Size: {len(file_bytes):,} bytes")
            logger.debug(f"  Content-Type: {content_type}")
            
            start_time = time.time()
            self.supabase.storage.from_("generated-media").upload(
                storage_path,
                file_bytes,
                file_options={"content-type": content_type}
            )
            elapsed = time.time() - start_time
            
            public_url = self.supabase.storage.from_("generated-media").get_public_url(storage_path)
            
            logger.info(f"✅ Uploaded to Supabase in {elapsed:.2f}s")
            logger.info(f"  Public URL: {public_url}")
            
            if metadata:
                await self._store_media_metadata(
                    initiative_id=initiative_id,
                    file_type=media_type[:-1],  # Remove 's' from 'images' or 'videos'
                    supabase_path=storage_path,
                    public_url=public_url,
                    metadata=metadata
                )
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload to Supabase: {e}")
            logger.debug(f"Initiative ID: {initiative_id}")
            logger.debug(f"Media type: {media_type}")
            raise
    
    async def _store_media_metadata(
        self,
        initiative_id: UUID,
        file_type: str,
        supabase_path: str,
        public_url: str,
        metadata: Dict[str, Any]
    ):
        """Store media file metadata in database"""
        try:
            logger.debug(f"Storing media metadata for {file_type}")
            db = DatabaseClient(initiative_id=str(initiative_id))
            
            # Extract execution_id from metadata if available
            execution_id = metadata.get('execution_id')
            execution_step = metadata.get('execution_step', 'Content Creation')
            
            result = await db.insert("media_files", {
                "initiative_id": str(initiative_id),
                "file_type": file_type,
                "supabase_path": supabase_path,
                "public_url": public_url,
                "prompt_used": metadata.get("prompt", ""),
                "metadata": metadata,
                # Add execution tracking
                "execution_id": execution_id,
                "execution_step": execution_step
            })
            logger.debug(f"Metadata stored successfully: {result}")
        except Exception as e:
            logger.error(f"Failed to store media metadata: {e}")
            # Don't raise - this is non-critical


class ImageGenerationService(MediaGenerationService):
    """Service for generating images using Wavespeed SDXL-LoRA"""
    
    async def generate_images(
        self,
        prompts: List[str],
        initiative_id: UUID,
        num_per_prompt: int = 1,
        size: str = "1024*1024"
    ) -> List[str]:
        """Generate images using Wavespeed and upload to Supabase"""
        urls = []
        
        logger.info(f"Starting image generation for {len(prompts)} prompts")
        
        async with aiohttp.ClientSession() as session:
            for i, prompt in enumerate(prompts, 1):
                logger.info(f"Processing prompt {i}/{len(prompts)}: {prompt[:50]}...")
                
                for j in range(num_per_prompt):
                    try:
                        logger.debug(f"Generating image {j+1}/{num_per_prompt} for prompt {i}")
                        
                        # Submit generation task
                        payload = {
                            "prompt": prompt,
                            "size": size,
                            "guidance_scale": 7.5,
                            "num_inference_steps": 30,
                            "seed": -1,
                            "enable_base64_output": False,
                            "loras": []
                        }
                        
                        request_id = await self._submit_task(
                            session,
                            settings.WAVESPEED_IMAGE_MODEL,
                            payload
                        )
                        
                        # Poll for completion
                        output_url = await self._poll_for_result(session, request_id)
                        
                        if output_url:
                            # Download the generated image
                            image_bytes = await self._download_media(session, output_url)
                            
                            # Upload to Supabase
                            public_url = await self._upload_to_supabase(
                                file_bytes=image_bytes,
                                initiative_id=initiative_id,
                                media_type="images",
                                file_extension="png",
                                content_type="image/png",
                                metadata={
                                    "prompt": prompt,
                                    "size": size,
                                    "model": settings.WAVESPEED_IMAGE_MODEL,
                                    "wavespeed_url": output_url,
                                    "request_id": request_id,
                                    # Add execution tracking if available
                                    "execution_id": getattr(self, 'execution_id', None),
                                    "execution_step": getattr(self, 'execution_step', None)
                                }
                            )
                            urls.append(public_url)
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to generate image for prompt '{prompt}': {e}")
                        # Continue with next prompt instead of failing completely
                        continue
        
        logger.info(f"✅ Image generation complete. Generated {len(urls)} images")
        return urls


class VideoGenerationService(MediaGenerationService):
    """Service for generating videos using Wavespeed WAN-2.2"""
    
    async def generate_video(
        self,
        prompt: str,
        initiative_id: UUID,
        duration_sec: int = 5,
        resolution: str = "720p",
        input_image_url: Optional[str] = None
    ) -> str:
        """Generate a video using Wavespeed and upload to Supabase"""
        try:
            logger.info(f"Starting video generation")
            logger.debug(f"Prompt: {prompt}")
            logger.debug(f"Duration: {duration_sec}s")
            logger.debug(f"Resolution: {resolution}")
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout for video
            ) as session:
                # If no input image provided, generate one first
                if not input_image_url:
                    logger.info("No input image provided, generating one from prompt...")
                    image_service = ImageGenerationService()
                    image_urls = await image_service.generate_images(
                        prompts=[prompt],
                        initiative_id=initiative_id,
                        num_per_prompt=1
                    )
                    if image_urls:
                        input_image_url = image_urls[0]
                        logger.info(f"Generated input image: {input_image_url}")
                    else:
                        raise ValueError("Failed to generate input image for video")
                else:
                    logger.debug(f"Using provided input image: {input_image_url}")
                
                # Submit video generation task
                payload = {
                    "image": input_image_url,
                    "prompt": prompt,
                    "seed": -1
                }
                
                request_id = await self._submit_task(
                    session,
                    settings.WAVESPEED_VIDEO_MODEL,
                    payload
                )
                
                # Poll for completion (videos take longer)
                logger.info("Waiting for video generation to complete...")
                output_url = await self._poll_for_result(session, request_id)
                
                if output_url:
                    logger.info(f"Video generation complete: {output_url}")
                    
                    # Download the generated video
                    logger.info("Downloading generated video...")
                    video_bytes = await self._download_media(session, output_url)
                    
                    # Upload to Supabase
                    logger.info("Uploading video to Supabase...")
                    public_url = await self._upload_to_supabase(
                        file_bytes=video_bytes,
                        initiative_id=initiative_id,
                        media_type="videos",
                        file_extension="mp4",
                        content_type="video/mp4",
                        metadata={
                            "prompt": prompt,
                            "duration_seconds": duration_sec,
                            "resolution": resolution,
                            "model": settings.WAVESPEED_VIDEO_MODEL,
                            "wavespeed_url": output_url,
                            "input_image": input_image_url,
                            "request_id": request_id
                        }
                    )
                    
                    logger.info(f"✅ Video generation complete: {public_url}")
                    return public_url
                else:
                    raise ValueError("No video URL returned from Wavespeed")
                    
        except asyncio.TimeoutError:
            logger.error(f"Video generation timeout after 10 minutes")
            raise Exception("Video generation timeout")
        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            raise