# agents/content_creator/prompt_builder.py


from typing import Dict, Any, Optional
from backend.config.settings import settings
import json
import logging

logger = logging.getLogger(__name__)


class ContentCreatorPromptBuilder:
    """Builds dynamic prompts for content creator agent"""
    
    def __init__(self, initiative_id: str):
        self.initiative_id = initiative_id
        self.base_prompt_path = "agents/content_creator/prompts/system_prompt.txt"
    
    def get_system_prompt(self) -> str:
        """Build complete system prompt with content limits"""
        base_prompt = self._load_base_prompt()
        
        limits = f"""

CONTENT CREATION LIMITS:
========================

PER AD SET LIMITS:
- Maximum Facebook posts: {settings.MAX_FACEBOOK_POSTS_PER_AD_SET}
- Maximum Instagram posts: {settings.MAX_INSTAGRAM_POSTS_PER_AD_SET}
- Maximum photos total: {settings.MAX_PHOTOS_PER_AD_SET}
- Maximum videos total: {settings.MAX_VIDEOS_PER_AD_SET}

PER POST LIMITS:
- Maximum photos per post: {settings.MAX_PHOTOS_PER_POST}
- Maximum videos per post: {settings.MAX_VIDEOS_PER_POST}
- Instagram caption max: 2200 characters
- Hashtags: 20-30 for Instagram, 3-5 for Facebook

OUTPUT STRUCTURE REQUIREMENTS:
- Must provide ContentBatch with all required fields
- batch_id: Unique UUID for the batch
- ad_set_id: ID of the ad set this content is for
- posts: Array of Post objects
- theme: Content theme for the batch
- target_audience: Description of target audience

EACH POST MUST INCLUDE:
- post_id: Unique UUID
- post_type: One of [IMAGE, VIDEO, CAROUSEL, REEL, LINK, TEXT]
- content: PostContent with caption, hashtags, links
- media: Array of MediaSpec with generation prompts
- schedule: PostSchedule with timing
- status: Post status (default: DRAFT)
- generation_metadata: Metadata about generation

CRITICAL RULES:
1. NEVER exceed remaining capacity limits
2. Adapt content for different post formats
3. Include clear calls-to-action
4. Ensure all content is platform-appropriate
5. Use research-validated hashtags and links
"""
        
        return base_prompt + limits
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Build user prompt with content context"""
        ad_set = input_data.get("ad_set", {})
        campaign = input_data.get("campaign", {})
        context = input_data.get("context", {})
        
        remaining_capacity = context.get("remaining_capacity", {})
        
        prompt = f"""
Create a ContentBatch for the following ad set:

CAMPAIGN INFORMATION:
====================
Name: {campaign.get('name', 'Unknown')}
Objective: {campaign.get('objective', 'Unknown')}
Budget: ${campaign.get('lifetime_budget', 0)}

AD SET INFORMATION:
==================
Name: {ad_set.get('name', 'Unknown')}
ID: {ad_set.get('id', 'Unknown')}
Post Volume Requested: {ad_set.get('post_volume', 3)}
Post Frequency: {ad_set.get('post_frequency', 3)} per week
Placements: {json.dumps(ad_set.get('placements', []))}

TARGET AUDIENCE:
===============
{self._format_target_audience(ad_set.get('target_audience', {}))}

CREATIVE BRIEF:
==============
{self._format_creative_brief(ad_set.get('creative_brief', {}))}

MATERIALS:
=========
{self._format_materials(ad_set.get('materials', {}))}

REMAINING CAPACITY (DO NOT EXCEED):
===================================
- Facebook posts: {remaining_capacity.get('facebook_posts', 0)}
- Instagram posts: {remaining_capacity.get('instagram_posts', 0)}
- Photos: {remaining_capacity.get('photos', 0)}
- Videos: {remaining_capacity.get('videos', 0)}

REQUIREMENTS FOR YOUR OUTPUT:
=============================
1. Create posts that fit within remaining capacity
2. Include variety in post types (image, video, carousel)
3. Write engaging captions with appropriate hashtags
4. Provide detailed media generation prompts
5. Schedule posts at optimal times
6. Ensure all content aligns with campaign objectives

Create a ContentBatch with posts that will engage the target audience.
"""
        
        if error_feedback:
            prompt += f"""

IMPORTANT - PREVIOUS ATTEMPT FAILED:
====================================
{error_feedback}

Please correct this issue and ensure you stay within capacity limits.
"""
        
        return prompt
    
    def _load_base_prompt(self) -> str:
        """Load base system prompt from file"""
        try:
            with open(self.base_prompt_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load base prompt: {e}")
            return """You are an expert social media content creator AI specializing in creating 
engaging posts for Facebook and Instagram."""
    
    def _format_target_audience(self, audience: Dict[str, Any]) -> str:
        """Format target audience"""
        if not audience:
            return "General audience"
        
        lines = []
        if audience.get('age_range'):
            lines.append(f"Age: {audience['age_range'][0]}-{audience['age_range'][1]}")
        if audience.get('locations'):
            lines.append(f"Locations: {', '.join(audience['locations'][:3])}")
        if audience.get('interests'):
            lines.append(f"Interests: {', '.join(audience['interests'][:5])}")
        if audience.get('languages'):
            lines.append(f"Languages: {', '.join(audience['languages'][:3])}")
        
        return "\n".join(lines) if lines else "General audience"
    
    def _format_creative_brief(self, brief: Dict[str, Any]) -> str:
        """Format creative brief"""
        if not brief:
            return "No specific creative direction"
        
        lines = []
        if brief.get('theme'):
            lines.append(f"Theme: {brief['theme']}")
        if brief.get('tone'):
            lines.append(f"Tone: {brief['tone']}")
        if brief.get('key_messages'):
            lines.append(f"Key Messages: {', '.join(brief['key_messages'][:3])}")
        if brief.get('call_to_action'):
            lines.append(f"Call to Action: {brief['call_to_action']}")
        
        return "\n".join(lines) if lines else "No specific creative direction"
    
    def _format_materials(self, materials: Dict[str, Any]) -> str:
        """Format available materials"""
        if not materials:
            return "No specific materials provided"
        
        lines = []
        if materials.get('links'):
            lines.append(f"Links: {', '.join(materials['links'][:3])}")
        if materials.get('hashtags'):
            hashtags = materials['hashtags'][:10]
            lines.append(f"Hashtags: {', '.join(hashtags)}")
        if materials.get('brand_assets'):
            lines.append(f"Brand Assets: {len(materials['brand_assets'])} available")
        
        return "\n".join(lines) if lines else "No specific materials provided"
