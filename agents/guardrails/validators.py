# agents/guardrails/validators.py

"""
Validators for agent outputs to ensure they comply with configured limits.
Each validator returns (is_valid, error_message).
"""

from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone
from urllib.parse import urlparse
from backend.config.settings import settings
import json
import logging

logger = logging.getLogger(__name__)


class BaseValidator:
    """Base class for all validators"""
    
    def validate(self, output: Any, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate agent output.
        
        Args:
            output: Agent's output to validate
            context: Full initiative context from InitiativeLoader
            
        Returns:
            (is_valid, error_message)
        """
        raise NotImplementedError


class ResearcherValidator(BaseValidator):
    """Validates researcher agent outputs"""
    
    def validate(self, output: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate research output"""
        try:
            # Check output structure
            if not isinstance(output, dict):
                return False, "Output must be a dictionary"
            
            required_fields = ["summary", "key_findings", "recommended_hashtags"]
            missing_fields = [f for f in required_fields if f not in output]
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Check output length (use custom encoder for datetime objects)
            output_str = json.dumps(output, default=str)
            if len(output_str) > settings.MAX_RESEARCH_OUTPUT_LENGTH:
                return False, (
                    f"Research output exceeds maximum length. "
                    f"Current: {len(output_str)} characters, "
                    f"Maximum: {settings.MAX_RESEARCH_OUTPUT_LENGTH} characters"
                )
            
            # Validate URLs in sources
            sources = output.get("sources", [])
            invalid_urls = []
            
            for source in sources:
                # Handle both dict (from structured output) and string formats
                if isinstance(source, dict):
                    url = source.get("url", "")
                    if not self._is_valid_url(url):
                        invalid_urls.append(url)
                elif isinstance(source, str):
                    if not self._is_valid_url(source):
                        invalid_urls.append(source)
                else:
                    return False, f"Invalid source format: must be dict or string, got {type(source)}"
            
            if invalid_urls:
                return False, f"Invalid URLs in sources: {', '.join(invalid_urls[:3])}"
            
            # Validate key findings structure
            key_findings = output.get("key_findings", [])
            if not isinstance(key_findings, list):
                return False, "key_findings must be a list"
            
            for i, finding in enumerate(key_findings):
                if not isinstance(finding, dict):
                    return False, f"key_findings[{i}] must be a dictionary"
                
                if "finding" not in finding:
                    return False, f"key_findings[{i}] missing 'finding' field"
            
            # Validate hashtags (handle both dict and string formats)
            hashtags = output.get("recommended_hashtags", [])
            if not isinstance(hashtags, list):
                return False, "recommended_hashtags must be a list"
            
            # Count hashtags properly whether they're dicts or strings
            hashtag_count = len(hashtags)
            
            if hashtag_count > settings.MAX_HASHTAGS:
                return False, (
                    f"Too many hashtags. "
                    f"Current: {hashtag_count}, Maximum: {settings.MAX_HASHTAGS}"
                )
            
            # Validate hashtag format
            for i, hashtag in enumerate(hashtags):
                if isinstance(hashtag, dict):
                    # It's a HashtagRecommendation object converted to dict
                    if "hashtag" not in hashtag:
                        return False, f"recommended_hashtags[{i}] missing 'hashtag' field"
                elif isinstance(hashtag, str):
                    # It's a simple string hashtag
                    pass
                else:
                    return False, f"Invalid hashtag format at index {i}: must be dict or string"
            
            logger.info("✅ Research output validated successfully")
            return True, None
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation failed: {str(e)}"
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid"""
        try:
            if not url:
                return False
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

# agents/guardrails/validators.py

class PlannerValidator(BaseValidator):
    """Validates planner agent outputs against campaign/ad set limits"""
    
    def validate(self, output: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate planner output against configured limits"""
        try:
            # Check basic structure
            if not isinstance(output, dict):
                return False, "Output must be a dictionary"
            
            if "campaigns" not in output:
                return False, "Output missing 'campaigns' field"
            
            campaigns = output.get("campaigns", [])
            if not isinstance(campaigns, list):
                return False, "'campaigns' must be a list"
            
            # Get current counts from context
            current_stats = context.get("statistics", {})
            current_active_campaigns = current_stats.get("active_campaigns", 0)
            
            # Count proposed active entities
            proposed_active_campaigns = 0
            campaign_ad_set_counts = {}
            
            now = datetime.now(timezone.utc)
            
            for campaign in campaigns:
                if not isinstance(campaign, dict):
                    return False, "Each campaign must be a dictionary"
                
                # Check if campaign would be active
                if self._would_be_active(campaign, now):
                    proposed_active_campaigns += 1
                    
                    # Count active ad sets in this campaign
                    ad_sets = campaign.get("ad_sets", [])
                    active_ad_sets = 0
                    
                    for ad_set in ad_sets:
                        if self._would_be_active(ad_set, now):
                            active_ad_sets += 1
                    
                    campaign_ad_set_counts[campaign.get("name", "Unknown")] = active_ad_sets
            
            # Calculate total active campaigns (existing + proposed new ones)
            total_active = current_active_campaigns + proposed_active_campaigns
            
            # Validate campaign count limits
            if total_active > settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE:
                return False, (
                    f"Campaign limit exceeded. "
                    f"Current active: {current_active_campaigns}, "
                    f"Proposed new: {proposed_active_campaigns}, "
                    f"Total would be: {total_active}, "
                    f"Maximum allowed: {settings.MAX_ACTIVE_CAMPAIGNS_PER_INITIATIVE}"
                )
            
            if total_active < settings.MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE:
                return False, (
                    f"Insufficient active campaigns. "
                    f"Total active: {total_active}, "
                    f"Minimum required: {settings.MIN_ACTIVE_CAMPAIGNS_PER_INITIATIVE}"
                )
            
            # Validate ad set counts per campaign
            for campaign_name, ad_set_count in campaign_ad_set_counts.items():
                if ad_set_count > settings.MAX_ACTIVE_AD_SETS_PER_CAMPAIGN:
                    return False, (
                        f"Ad set limit exceeded for campaign '{campaign_name}'. "
                        f"Active ad sets: {ad_set_count}, "
                        f"Maximum allowed: {settings.MAX_ACTIVE_AD_SETS_PER_CAMPAIGN}"
                    )
                
                if ad_set_count < settings.MIN_ACTIVE_AD_SETS_PER_CAMPAIGN:
                    return False, (
                        f"Insufficient ad sets for campaign '{campaign_name}'. "
                        f"Active ad sets: {ad_set_count}, "
                        f"Minimum required: {settings.MIN_ACTIVE_AD_SETS_PER_CAMPAIGN}"
                    )
            
            # FIX: Safely validate budget allocation
            total_budget_allocated = output.get("total_budget_allocated", 0)
            initiative = context.get("initiative", {})
            
            # Handle None values safely
            total_budget_obj = initiative.get("total_budget")
            if total_budget_obj and isinstance(total_budget_obj, dict):
                max_budget = total_budget_obj.get("amount", 0)
            else:
                # If no budget defined, skip budget validation
                max_budget = float('inf')  # Or use a default from settings
                logger.debug("No budget limit defined for initiative, skipping budget validation")
            
            if max_budget != float('inf') and total_budget_allocated > max_budget:
                return False, (
                    f"Budget allocation exceeds limit. "
                    f"Allocated: ${total_budget_allocated}, "
                    f"Maximum: ${max_budget}"
                )
            
            logger.info(f"✅ Planner output validated: {proposed_active_campaigns} campaigns, "
                       f"{sum(campaign_ad_set_counts.values())} total ad sets")
            return True, None
            
        except Exception as e:
            logger.error(f"Planner validation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, f"Validation failed: {str(e)}"
    
    def _would_be_active(self, entity: Dict[str, Any], now: datetime) -> bool:
        """Check if an entity would be active based on its configuration"""
        # Check explicit status
        status = entity.get("status", "draft").lower()
        if status in ["paused", "stopped", "completed", "archived"]:
            return False
        
        # Check is_active flag if present
        if "is_active" in entity and not entity["is_active"]:
            return False
        
        # FIX: Use 'or {}' instead of get default to handle None
        schedule = entity.get("schedule") or {}
        
        start_date = self._parse_datetime(schedule.get("start_date"))
        end_date = self._parse_datetime(schedule.get("end_date"))
        
        # If no dates specified, consider it active
        if not start_date and not end_date:
            return True
        
        if start_date and start_date > now:
            return False  # Not started yet
        
        if end_date and end_date < now:
            return False  # Already ended
        
        return True
    
    def _parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if not dt_value:
            return None
        
        if isinstance(dt_value, datetime):
            return dt_value if dt_value.tzinfo else dt_value.replace(tzinfo=timezone.utc)
        
        if isinstance(dt_value, str):
            try:
                if 'T' in dt_value:
                    dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(dt_value, "%Y-%m-%d")
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except:
                return None
        
        return None


class ContentCreatorValidator(BaseValidator):
    """Validates content creator outputs"""
    
    def validate(self, output: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate content creator output"""
        try:
            # Check basic structure
            if not isinstance(output, dict):
                return False, "Output must be a dictionary"
            
            if "posts" not in output:
                return False, "Output missing 'posts' field"
            
            posts = output.get("posts", [])
            if not isinstance(posts, list):
                return False, "'posts' must be a list"
            
            # Count posts by type
            post_counts = {
                "facebook": 0,
                "instagram": 0,
                "total_photos": 0,
                "total_videos": 0
            }
            
            for post in posts:
                if not isinstance(post, dict):
                    return False, "Each post must be a dictionary"
                
                # Check required fields
                required_fields = ["post_type", "text_content"]
                missing = [f for f in required_fields if f not in post]
                if missing:
                    return False, f"Post missing required fields: {', '.join(missing)}"
                
                # Count media
                post_type = post.get("post_type", "")
                media_urls = post.get("media_urls", [])
                
                # This is a simplified check - in reality, you'd check against
                # the specific ad_set limits using ContentGenerationState
                if post_type in ["image", "carousel"]:
                    post_counts["total_photos"] += len(media_urls)
                elif post_type in ["video", "reel"]:
                    post_counts["total_videos"] += len(media_urls)
                
                # Check per-post media limits
                if post_type == "carousel" and len(media_urls) > 10:
                    return False, f"Carousel post exceeds 10 image limit"
                
                if post_type == "video" and len(media_urls) > settings.MAX_VIDEOS_PER_POST:
                    return False, (
                        f"Video post exceeds limit. "
                        f"Has {len(media_urls)} videos, "
                        f"maximum: {settings.MAX_VIDEOS_PER_POST}"
                    )
            
            # Note: More detailed validation would be done at the tool level
            # using ContentGenerationState for specific ad_set limits
            
            logger.info(f"✅ Content output validated: {len(posts)} posts")
            return True, None
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False, f"Validation failed: {str(e)}"


# Factory function to get appropriate validator
def get_validator(agent_type: str) -> BaseValidator:
    """Get the appropriate validator for an agent type"""
    validators = {
        "researcher": ResearcherValidator(),
        "planner": PlannerValidator(),
        "content_creator": ContentCreatorValidator()
    }
    
    validator = validators.get(agent_type)
    if not validator:
        raise ValueError(f"No validator found for agent type: {agent_type}")
    
    return validator