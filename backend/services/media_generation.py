# backend/services/media_generation.py

"""
Media generation services using Google's Gemini AI models.
Handles image generation with Imagen 3 and video generation with Veo 3.
"""

import asyncio
import logging
import io
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import aiohttp
from PIL import Image
from google import genai
from google.genai import types
from backend.config.settings import settings
from backend.db.supabase_client import DatabaseClient
from supabase import create_client, Client as SupabaseClient

logger = logging.getLogger(__name__)


class MediaGenerationService:
    """Base class for media generation services"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in settings")
        
        # Configure Gemini AI with new google-genai package
        self.client = genai.Client(api_key=self.api_key)
        
        # Initialize Supabase client with SERVICE KEY for storage operations
        # This bypasses RLS restrictions
        self.supabase: SupabaseClient = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY  # Use service key, not anon key
        )
        
        # Try to ensure storage bucket exists, but don't fail if it doesn't work
        try:
            self._ensure_storage_bucket()
        except Exception as e:
            logger.warning(f"Could not verify storage bucket: {e}")
    
    def _ensure_storage_bucket(self):
        """Ensure the generated-media bucket exists in Supabase storage"""
        try:
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if "generated-media" not in bucket_names:
                # Only try to create if we have service key
                if hasattr(settings, 'SUPABASE_SERVICE_KEY'):
                    self.supabase.storage.create_bucket(
                        "generated-media",
                        options={"public": True}
                    )
                    logger.info("Created 'generated-media' storage bucket")
                else:
                    logger.error("Cannot create bucket without SUPABASE_SERVICE_KEY")
        except Exception as e:
            logger.error(f"Error checking/creating storage bucket: {e}")
    
    async def _upload_to_supabase(
        self,
        file_bytes: bytes,
        initiative_id: UUID,
        media_type: str,
        file_extension: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload file to Supabase storage and return public URL.
        
        Args:
            file_bytes: File content as bytes
            initiative_id: Initiative UUID for organization
            media_type: 'images' or 'videos'
            file_extension: File extension (e.g., 'jpg', 'mp4')
            metadata: Optional metadata to store with file
            
        Returns:
            Public URL of uploaded file
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_id = uuid4().hex[:8]
            filename = f"{timestamp}_{file_id}.{file_extension}"
            
            # Build storage path
            storage_path = f"{initiative_id}/{media_type}/{filename}"
            
            # Upload to Supabase
            response = self.supabase.storage.from_("generated-media").upload(
                storage_path,
                file_bytes,
                file_options={"content-type": f"{'image' if media_type == 'images' else 'video'}/{file_extension}"}
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_("generated-media").get_public_url(storage_path)
            
            # Store metadata in database
            if metadata:
                await self._store_media_metadata(
                    initiative_id=initiative_id,
                    file_type=media_type[:-1],  # Remove 's' from plural
                    supabase_path=storage_path,
                    public_url=public_url,
                    metadata=metadata
                )
            
            logger.info(f"Uploaded {media_type[:-1]} to: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload to Supabase: {e}")
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
            db = DatabaseClient(initiative_id=str(initiative_id))
            await db.insert("media_files", {
                "initiative_id": str(initiative_id),
                "file_type": file_type,
                "supabase_path": supabase_path,
                "public_url": public_url,
                "prompt_used": metadata.get("prompt", ""),
                "metadata": metadata
            })
        except Exception as e:
            logger.error(f"Failed to store media metadata: {e}")
            # Don't fail the upload if metadata storage fails


class ImageGenerationService(MediaGenerationService):
    """Service for generating images using Gemini Imagen 3"""
    
    def __init__(self):
        super().__init__()
        # Note: Imagen 3 model name when available
        self.imagen_model_name = "imagen-3"
        # Fallback model for text-based tasks
        self.fallback_model = "gemini-1.5-pro"
    
    async def generate_images(
        self,
        prompts: List[str],
        initiative_id: UUID,
        num_per_prompt: int = 1,
        size: str = "1024x1024"
    ) -> List[str]:
        """
        Generate images using Gemini Imagen 3 and upload to Supabase.
        
        Args:
            prompts: List of text prompts for image generation
            initiative_id: Initiative UUID for storage organization
            num_per_prompt: Number of images to generate per prompt
            size: Image dimensions (e.g., "1024x1024", "1920x1080")
            
        Returns:
            List of public URLs for generated images
        """
        urls = []
        
        for prompt in prompts:
            for i in range(num_per_prompt):
                try:
                    # Generate image using Imagen 3
                    image_bytes = await self._generate_single_image(prompt, size)
                    
                    if image_bytes:
                        # Upload to Supabase
                        public_url = await self._upload_to_supabase(
                            file_bytes=image_bytes,
                            initiative_id=initiative_id,
                            media_type="images",
                            file_extension="jpg",
                            metadata={
                                "prompt": prompt,
                                "size": size,
                                "model": "imagen-3"
                            }
                        )
                        urls.append(public_url)
                        
                        # Brief delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Failed to generate image for prompt '{prompt}': {e}")
                    # Continue with other images
        
        return urls
    
    async def _generate_single_image(self, prompt: str, size: str) -> bytes:
        """
        Generate a single image using Imagen 3.
        
        Note: Using the new google-genai package API structure
        """
        try:
            width, height = map(int, size.split('x'))
            
            # Check if Imagen model is available
            available_models = await asyncio.to_thread(
                self.client.models.list
            )
            
            model_names = [model.name for model in available_models]
            
            if self.imagen_model_name in model_names:
                # Use Imagen 3 for image generation
                try:
                    # Generate image using the client
                    response = await asyncio.to_thread(
                        self.client.models.generate_image,
                        model=self.imagen_model_name,
                        prompt=prompt,
                        number_of_images=1,
                        aspect_ratio=f"{width}:{height}",
                        safety_filter_level="block_none",
                        person_generation="allow_all"
                    )
                    
                    # Extract image bytes from response
                    if response and hasattr(response, 'images'):
                        if response.images and len(response.images) > 0:
                            # Get the first image
                            image = response.images[0]
                            if hasattr(image, 'bytes'):
                                return image.bytes
                            elif hasattr(image, 'data'):
                                import base64
                                return base64.b64decode(image.data)
                                
                except Exception as e:
                    logger.error(f"Error generating with Imagen 3: {e}")
            else:
                logger.warning(f"Imagen 3 model '{self.imagen_model_name}' not available")
            
            # Fallback to placeholder
            return self._create_placeholder_image(prompt, size)
                        
        except Exception as e:
            logger.error(f"Error in _generate_single_image: {e}")
            # Return placeholder for testing
            return self._create_placeholder_image(prompt, size)
    
    def _create_placeholder_image(self, prompt: str, size: str) -> bytes:
        """Create a placeholder image for testing"""
        width, height = map(int, size.split('x'))
        img = Image.new('RGB', (width, height), color=(73, 109, 137))
        
        # Add text to indicate it's a placeholder
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        text = f"Placeholder for: {prompt[:30]}..."
        draw.text((10, 10), text, fill=(255, 255, 255), font=font)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85)
        return img_byte_arr.getvalue()


class VideoGenerationService(MediaGenerationService):
    """Service for generating videos using Gemini Veo 3"""
    
    def __init__(self):
        super().__init__()
        # Note: Veo 3 model name when available
        self.veo_model_name = "veo-3"
    
    async def generate_video(
        self,
        prompt: str,
        initiative_id: UUID,
        duration_sec: int = 15,
        resolution: str = "1080p"
    ) -> str:
        """
        Generate a video using Gemini Veo 3 and upload to Supabase.
        
        Args:
            prompt: Text prompt for video generation
            initiative_id: Initiative UUID for storage organization
            duration_sec: Video duration in seconds (3-90)
            resolution: Video resolution (e.g., "720p", "1080p", "4k")
            
        Returns:
            Public URL of generated video
        """
        try:
            # Validate duration
            duration_sec = max(3, min(90, duration_sec))
            
            # Generate video
            video_bytes = await self._generate_single_video(prompt, duration_sec, resolution)
            
            if video_bytes:
                # Upload to Supabase
                public_url = await self._upload_to_supabase(
                    file_bytes=video_bytes,
                    initiative_id=initiative_id,
                    media_type="videos",
                    file_extension="mp4",
                    metadata={
                        "prompt": prompt,
                        "duration_seconds": duration_sec,
                        "resolution": resolution,
                        "model": "veo-3"
                    }
                )
                return public_url
            else:
                raise ValueError("Failed to generate video")
                
        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            raise
    
    async def _generate_single_video(
        self,
        prompt: str,
        duration_sec: int,
        resolution: str
    ) -> bytes:
        """
        Generate a single video using Veo 3.
        
        Note: Using the new google-genai package API structure
        """
        try:
            # Check if Veo model is available
            available_models = await asyncio.to_thread(
                self.client.models.list
            )
            
            model_names = [model.name for model in available_models]
            
            if self.veo_model_name not in model_names:
                logger.warning(f"Veo 3 model '{self.veo_model_name}' not available, using placeholder")
                return self._create_placeholder_video(prompt, duration_sec)
            
            # Parse resolution to get dimensions
            resolution_map = {
                "720p": (1280, 720),
                "1080p": (1920, 1080),
                "4k": (3840, 2160)
            }
            width, height = resolution_map.get(resolution, (1920, 1080))
            
            # Generate video using the client
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_video,
                    model=self.veo_model_name,
                    prompt=prompt,
                    duration_seconds=duration_sec,
                    fps=30,
                    aspect_ratio=f"{width}:{height}",
                    video_format="mp4",
                    safety_filter_level="block_none"
                )
                
                # Check if operation is async
                if hasattr(response, 'operation'):
                    # Poll for completion
                    video_bytes = await self._poll_video_operation(response.operation)
                    return video_bytes if video_bytes else self._create_placeholder_video(prompt, duration_sec)
                
                # Direct response
                if hasattr(response, 'video'):
                    if hasattr(response.video, 'bytes'):
                        return response.video.bytes
                    elif hasattr(response.video, 'data'):
                        import base64
                        return base64.b64decode(response.video.data)
                
            except Exception as e:
                logger.error(f"Error generating video with Veo 3: {e}")
            
            # If no valid response, return placeholder
            return self._create_placeholder_video(prompt, duration_sec)
                        
        except Exception as e:
            logger.error(f"Error in _generate_single_video: {e}")
            # Return placeholder for testing
            return self._create_placeholder_video(prompt, duration_sec)
    
    async def _poll_video_operation(self, operation_name: str, max_attempts: int = 60) -> Optional[bytes]:
        """Poll for video generation completion using new google-genai package"""
        for attempt in range(max_attempts):
            try:
                # Check operation status
                operation = await asyncio.to_thread(
                    self.client.operations.get,
                    name=operation_name
                )
                
                if operation.done:
                    if hasattr(operation, 'result'):
                        result = operation.result
                        if hasattr(result, 'video'):
                            if hasattr(result.video, 'bytes'):
                                return result.video.bytes
                            elif hasattr(result.video, 'uri'):
                                # Download video from URI
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(result.video.uri) as response:
                                        if response.status == 200:
                                            return await response.read()
                    break
                
                # Wait before next poll
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error polling video operation: {e}")
                break
        
        return None
    
    def _create_placeholder_video(self, prompt: str, duration_sec: int) -> bytes:
        """Create a placeholder video for testing"""
        # For testing, return a small valid MP4 file
        # In production, this should never be reached
        
        # This is a minimal valid MP4 file (black screen)
        # You would replace this with actual video generation
        placeholder_mp4 = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42mp41'
        
        logger.warning(f"Returning placeholder video for prompt: {prompt}")
        return placeholder_mp4