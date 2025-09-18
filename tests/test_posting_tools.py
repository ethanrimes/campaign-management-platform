#!/usr/bin/env python3
"""
Test script for Facebook and Instagram content generation and posting.
Tests the actual executor classes with proper token management.

Usage:
    python tests/test_posting_tools.py --all              # Run all tests
    python tests/test_posting_tools.py --platform facebook  # Test Facebook only
    python tests/test_posting_tools.py --platform instagram # Test Instagram only
    python tests/test_posting_tools.py --test-type image   # Test image posts only
    python tests/test_posting_tools.py --test-type video   # Test video posts only
"""

import asyncio
import argparse
import logging
import sys
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.content_creator.tools.facebook_executor import FacebookExecutor
from agents.content_creator.tools.instagram_executor import InstagramExecutor
from agents.content_creator.tools.posting_service import PostingService
from agents.guardrails.state import ContentGenerationState
from backend.services.token_manager import TokenManager
from backend.db.supabase_client import DatabaseClient
from backend.config.settings import settings
from backend.config.logging_config import LoggingConfig

# Initialize logging
LoggingConfig.setup_logging(log_level="DEBUG")
logger = logging.getLogger(__name__)

# Test configuration
TEST_INITIATIVE_ID = UUID("bf2d9675-b236-4a86-8514-78b0b6d75a53")
EXECUTION_ID = str(UUID("597ad809-6a72-4965-a82c-2886617931a8"))  # For tracking


class PostingTestSuite:
    """Test suite for Facebook and Instagram posting"""
    
    def __init__(self):
        self.initiative_id = str(TEST_INITIATIVE_ID)
        self.execution_id = EXECUTION_ID
        self.token_manager = TokenManager(self.initiative_id)
        self.db_client = DatabaseClient(initiative_id=self.initiative_id)
        self.results = []
        
        # Initialize state for tracking
        self.state = ContentGenerationState(
            ad_set_id="test_ad_set",
            initial_counts={
                "facebook_posts": 0,
                "instagram_posts": 0,
                "photos": 0,
                "videos": 0
            }
        )
    
    async def setup(self):
        """Verify tokens are available and valid"""
        logger.info("=" * 80)
        logger.info("SETUP: Verifying tokens and configuration")
        logger.info("=" * 80)
        
        try:
            # Test Facebook tokens
            logger.info("Checking Facebook tokens...")
            fb_tokens = await self.token_manager.get_facebook_tokens()
            logger.info(f"✅ Facebook Page ID: {fb_tokens.get('page_id')}")
            logger.info(f"✅ Facebook Page Name: {fb_tokens.get('page_name', 'N/A')}")
            
            # Test Instagram tokens
            logger.info("Checking Instagram tokens...")
            ig_tokens = await self.token_manager.get_instagram_tokens()
            logger.info(f"✅ Instagram Business ID: {ig_tokens.get('business_id')}")
            logger.info(f"✅ Instagram Username: {ig_tokens.get('username', 'N/A')}")
            
            # Verify the actual token works
            await self._verify_instagram_token(ig_tokens.get('access_token'))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _verify_instagram_token(self, access_token: str):
        """Verify Instagram token with API call"""
        import aiohttp
        
        url = f"https://graph.instagram.com/v23.0/me"
        params = {
            "fields": "id,username",
            "access_token": access_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Token verified - Username: {data.get('username')}")
                else:
                    error = await response.text()
                    raise Exception(f"Token verification failed: {error}")
    
    async def test_facebook_image_post(self) -> Dict[str, Any]:
        """Test posting a single image to Facebook"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Facebook Single Image Post")
        logger.info("=" * 80)
        
        executor = FacebookExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_fb_image_001",
            "post_type": "image",
            "content": {
                "caption": "🎨 Testing Facebook image post with AI-generated art!",
                "hashtags": ["AIArt", "Automation", "Testing"]
            },
            "media": [{
                "url": "A beautiful sunset over mountains, photorealistic, golden hour",
                "format": "jpeg",
                "width": 1080,
                "height": 1080
            }]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Facebook Image", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_facebook_carousel_post(self) -> Dict[str, Any]:
        """Test posting a carousel (multiple images) to Facebook"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Facebook Carousel Post")
        logger.info("=" * 80)
        
        executor = FacebookExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_fb_carousel_001",
            "post_type": "carousel",
            "content": {
                "caption": "🖼️ Amazing carousel showcasing AI creativity!",
                "hashtags": ["Carousel", "MultipleImages", "AIGenerated"]
            },
            "media": [
                {"url": "Abstract geometric art with vibrant colors", "format": "jpeg"},
                {"url": "Minimalist zen garden design", "format": "jpeg"},
                {"url": "Futuristic cityscape at night", "format": "jpeg"}
            ]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Facebook Carousel", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_facebook_video_post(self) -> Dict[str, Any]:
        """Test posting a video to Facebook"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Facebook Video Post")
        logger.info("=" * 80)
        
        executor = FacebookExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_fb_video_001",
            "post_type": "video",
            "content": {
                "caption": "🎬 Check out this AI-generated video!",
                "hashtags": ["Video", "AIVideo", "Animation"]
            },
            "media": [{
                "url": "Smooth animation of colorful waves flowing",
                "format": "mp4",
                "duration_seconds": 5
            }]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Facebook Video", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_facebook_text_post(self) -> Dict[str, Any]:
        """Test posting text/link to Facebook"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Facebook Text/Link Post")
        logger.info("=" * 80)
        
        executor = FacebookExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_fb_text_001",
            "post_type": "link",
            "content": {
                "caption": "📢 Important update about our AI content platform!",
                "hashtags": ["Update", "Platform", "AI"],
                "links": ["https://example.com/ai-platform-update"]
            }
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Facebook Text/Link", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_instagram_image_post(self) -> Dict[str, Any]:
        """Test posting a single image to Instagram"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Instagram Single Image Post")
        logger.info("=" * 80)
        
        executor = InstagramExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_ig_image_001",
            "post_type": "image",
            "content": {
                "caption": "✨ Testing Instagram image post with AI art! #AIArt #Testing",
                "hashtags": ["AIArt", "InstagramTest", "Automation", "DigitalArt", "Creative"]
            },
            "media": [{
                "url": "Vibrant abstract art with flowing colors, Instagram square format",
                "format": "jpeg",
                "width": 1080,
                "height": 1080
            }]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Instagram Image", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_instagram_carousel_post(self) -> Dict[str, Any]:
        """Test posting a carousel to Instagram"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Instagram Carousel Post")
        logger.info("=" * 80)
        
        executor = InstagramExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_ig_carousel_001",
            "post_type": "carousel",
            "content": {
                "caption": "🎨 Swipe to see more AI creations! →",
                "hashtags": ["Carousel", "AIArt", "MultiPost", "Creative", "Design"]
            },
            "media": [
                {"url": "Colorful mandala pattern", "format": "jpeg"},
                {"url": "Geometric abstract design", "format": "jpeg"},
                {"url": "Nature-inspired digital art", "format": "jpeg"}
            ]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Instagram Carousel", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_instagram_reel_post(self) -> Dict[str, Any]:
        """Test posting a Reel to Instagram"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Instagram Reel Post")
        logger.info("=" * 80)
        
        executor = InstagramExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_ig_reel_001",
            "post_type": "reel",
            "content": {
                "caption": "🎬 AI-generated Reel! Watch the magic unfold ✨",
                "hashtags": ["Reels", "AIVideo", "Trending", "Creative", "Animation"]
            },
            "media": [{
                "url": "Dynamic animation with morphing shapes and colors",
                "format": "mp4",
                "duration_seconds": 15
            }]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Instagram Reel", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_instagram_story_post(self) -> Dict[str, Any]:
        """Test posting a Story to Instagram"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Instagram Story Post")
        logger.info("=" * 80)
        
        executor = InstagramExecutor(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        post_data = {
            "post_id": "test_ig_story_001",
            "post_type": "story",
            "content": {
                "caption": "",  # Stories don't have captions
                "hashtags": []
            },
            "media": [{
                "url": "Eye-catching story design with call-to-action, vertical format",
                "format": "jpeg",
                "width": 1080,
                "height": 1920
            }]
        }
        
        result = await executor.execute(post_data)
        
        self._log_result("Instagram Story", result)
        return result._asdict() if hasattr(result, '_asdict') else result.__dict__
    
    async def test_posting_service_batch(self) -> Dict[str, Any]:
        """Test the PostingService with a batch of posts"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Posting Service Batch Execution")
        logger.info("=" * 80)
        
        service = PostingService(
            initiative_id=self.initiative_id,
            state=self.state,
            execution_id=self.execution_id
        )
        
        posts = [
            {
                "post_id": "batch_001",
                "post_type": "image",
                "content": {
                    "caption": "Batch post 1",
                    "hashtags": ["Batch", "Test1"]
                },
                "media": [{"url": "Beautiful landscape", "format": "jpeg"}]
            },
            {
                "post_id": "batch_002",
                "post_type": "reel",
                "content": {
                    "caption": "Batch post 2",
                    "hashtags": ["Batch", "Test2"]
                },
                "media": [{"url": "Short animation", "format": "mp4", "duration_seconds": 10}]
            }
        ]
        
        results = await service.execute_batch(
            posts=posts,
            ad_set_id="test_ad_set",
            placements=["facebook_feed", "instagram_feed", "instagram_reels"]
        )
        
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        logger.info(f"Batch Results: {successful} successful, {failed} failed")
        
        return {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": [r._asdict() if hasattr(r, '_asdict') else r.__dict__ for r in results]
        }
    
    def _log_result(self, test_name: str, result):
        """Log test result"""
        if result.success:
            logger.info(f"✅ {test_name} - SUCCESS")
            logger.info(f"   Platform ID: {result.platform_post_id}")
            logger.info(f"   URL: {result.platform_url}")
            logger.info(f"   Media: {len(result.media_urls) if result.media_urls else 0} files")
        else:
            logger.error(f"❌ {test_name} - FAILED")
            logger.error(f"   Error: {result.error_message}")
        
        self.results.append({
            "test": test_name,
            "success": result.success,
            "platform_id": result.platform_post_id,
            "error": result.error_message
        })
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {successful}")
        logger.info(f"❌ Failed: {failed}")
        
        if failed > 0:
            logger.info("\nFailed Tests:")
            for result in self.results:
                if not result["success"]:
                    logger.error(f"  - {result['test']}: {result['error']}")
        
        logger.info("=" * 80)


async def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description="Test Facebook and Instagram posting")
    parser.add_argument("--platform", choices=["all", "facebook", "instagram"], 
                       default="all", help="Which platform to test")
    parser.add_argument("--test-type", choices=["all", "image", "video", "carousel", "text"],
                       default="all", help="Type of posts to test")
    parser.add_argument("--skip-setup", action="store_true", 
                       help="Skip token verification")
    
    args = parser.parse_args()
    
    # Initialize test suite
    suite = PostingTestSuite()
    
    # Setup and verify tokens
    if not args.skip_setup:
        setup_success = await suite.setup()
        if not setup_success:
            logger.error("Setup failed. Exiting.")
            return
    
    # Determine which tests to run
    tests_to_run = []
    
    # Facebook tests
    if args.platform in ["all", "facebook"]:
        if args.test_type in ["all", "image"]:
            tests_to_run.append(suite.test_facebook_image_post)
        if args.test_type in ["all", "carousel"]:
            tests_to_run.append(suite.test_facebook_carousel_post)
        if args.test_type in ["all", "video"]:
            tests_to_run.append(suite.test_facebook_video_post)
        if args.test_type in ["all", "text"]:
            tests_to_run.append(suite.test_facebook_text_post)
    
    # Instagram tests
    if args.platform in ["all", "instagram"]:
        if args.test_type in ["all", "image"]:
            tests_to_run.append(suite.test_instagram_image_post)
        if args.test_type in ["all", "carousel"]:
            tests_to_run.append(suite.test_instagram_carousel_post)
        if args.test_type in ["all", "video"]:
            tests_to_run.append(suite.test_instagram_reel_post)
        if args.test_type == "all":
            tests_to_run.append(suite.test_instagram_story_post)
    
    # Add batch test if testing all
    if args.platform == "all" and args.test_type == "all":
        tests_to_run.append(suite.test_posting_service_batch)
    
    # Execute tests
    for test in tests_to_run:
        try:
            await test()
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            logger.error(traceback.format_exc())
            suite.results.append({
                "test": test.__name__,
                "success": False,
                "platform_id": None,
                "error": str(e)
            })
    
    # Print summary
    suite.print_summary()


if __name__ == "__main__":
    asyncio.run(main())