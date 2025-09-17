# agents/content_creator/agent.py

from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel
from agents.base.agent import BaseAgent, AgentConfig
from agents.content_creator.models import ContentBatch
from agents.content_creator.prompt_builder import ContentCreatorPromptBuilder
from agents.content_creator.tools.facebook import (
    FacebookTextLinkPostTool, FacebookImagePostTool, FacebookVideoPostTool
)
from agents.content_creator.tools.instagram import (
    InstagramImagePostTool, InstagramReelPostTool
)
from backend.db.supabase_client import DatabaseClient
from agents.guardrails.state import ContentGenerationState
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """Content creator with structured output and guardrails"""
    
    def __init__(self, config: AgentConfig):
        self.db_client = DatabaseClient(initiative_id=config.initiative_id)
        self.prompt_builder = ContentCreatorPromptBuilder(config.initiative_id)
        self.generation_state = None  # Injected by orchestrator
        self.tools_by_ad_set = {}
        super().__init__(config)
    
    def _initialize_tools(self) -> List[Any]:
        """Tools are initialized per ad_set"""
        return []
    
    def get_output_model(self) -> Type[BaseModel]:
        """Return ContentBatch model for structured output"""
        return ContentBatch
    
    def get_system_prompt(self) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.get_system_prompt()
    
    def build_user_prompt(self, input_data: Dict[str, Any], error_feedback: Optional[str] = None) -> str:
        """Delegate to prompt builder"""
        return self.prompt_builder.build_user_prompt(input_data, error_feedback)
    
    def _get_or_create_tools(self, ad_set_id: str) -> Dict[str, Any]:
        """Get or create tools with state validation"""
        if ad_set_id not in self.tools_by_ad_set:
            ad_set_state = None
            if self.generation_state:
                ad_set_state = self.generation_state.get_ad_set_state(ad_set_id)
            
            self.tools_by_ad_set[ad_set_id] = {
                'facebook_text': FacebookTextLinkPostTool(state=ad_set_state),
                'facebook_image': FacebookImagePostTool(state=ad_set_state),
                'facebook_video': FacebookVideoPostTool(state=ad_set_state),
                'instagram_image': InstagramImagePostTool(state=ad_set_state),
                'instagram_reel': InstagramReelPostTool(state=ad_set_state)
            }
            
            # Pass execution tracking
            for tool in self.tools_by_ad_set[ad_set_id].values():
                tool.execution_id = self.execution_id
                tool.execution_step = self.execution_step
        
        return self.tools_by_ad_set[ad_set_id]
    
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content creation with guardrails"""
        logger.info("=" * 70)
        logger.info("CONTENT CREATOR STARTING (WITH GUARDRAILS)")
        logger.info("=" * 70)
        
        campaigns = input_data.get("campaigns", [])
        if not campaigns:
            return {"posts_created": 0, "posts": [], "errors": []}
        
        all_posts = []
        all_errors = []
        
        for campaign in campaigns:
            for ad_set in campaign.get("ad_sets", []):
                ad_set_id = ad_set.get("id")
                if not ad_set_id:
                    continue
                
                logger.info(f"Creating content for ad set: {ad_set.get('name')}")
                
                # Get tools with state validation
                tools = self._get_or_create_tools(ad_set_id)
                
                # Gather context with remaining capacity
                context = await self._gather_context(ad_set_id)
                
                # Prepare input for content generation
                content_input = {
                    "ad_set": ad_set,
                    "campaign": campaign,
                    "context": context
                }
                
                try:
                    # Generate content batch with structured output
                    content_batch = await self.execute_with_retries(content_input)
                    
                    # Validate against capacity
                    if self._validate_content_batch(content_batch, context):
                        # Execute content creation
                        posts, errors = await self._execute_content_batch(
                            content_batch, ad_set_id, tools
                        )
                        all_posts.extend(posts)
                        all_errors.extend(errors)
                    else:
                        all_errors.append(f"Content exceeds limits for ad set {ad_set_id}")
                        
                except Exception as e:
                    all_errors.append(f"Failed to create content: {str(e)}")
        
        return {
            "posts_created": len(all_posts),
            "posts": all_posts,
            "errors": all_errors,
            "generation_summary": self.generation_state.get_all_summaries() if self.generation_state else {}
        }
    
    def validate_output(self, output: Any) -> bool:
        """Validate ContentBatch structure"""
        if not isinstance(output, dict):
            return False
        
        # Check required fields for ContentBatch
        required_fields = ["batch_id", "ad_set_id", "posts", "theme", "target_audience"]
        if not all(field in output for field in required_fields):
            return False
        
        # Check posts array
        posts = output.get("posts", [])
        if not isinstance(posts, list) or len(posts) == 0:
            return False
        
        return True
    
    def _validate_content_batch(self, batch: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate content against remaining capacity"""
        remaining = context.get("remaining_capacity", {})
        
        # Count posts by type
        facebook_count = sum(1 for p in batch.get("posts", []) if "facebook" in str(p))
        instagram_count = sum(1 for p in batch.get("posts", []) if "instagram" in str(p))
        
        # Check limits
        if facebook_count > remaining.get('facebook_posts', 0):
            return False
        if instagram_count > remaining.get('instagram_posts', 0):
            return False
        
        return True
    
    async def _gather_context(self, ad_set_id: str) -> Dict[str, Any]:
        """Gather context including remaining capacity"""
        ad_sets = await self.db_client.select("ad_sets", filters={"id": ad_set_id})
        ad_set = ad_sets[0] if ad_sets else {}
        
        campaigns = []
        if ad_set:
            campaigns = await self.db_client.select(
                "campaigns",
                filters={"id": ad_set.get("campaign_id")}
            )
        
        remaining_capacity = {}
        if self.generation_state:
            ad_set_state = self.generation_state.get_ad_set_state(ad_set_id)
            if ad_set_state:
                remaining_capacity = ad_set_state.get_remaining_capacity()
        
        return {
            "ad_set": ad_set,
            "campaign": campaigns[0] if campaigns else {},
            "remaining_capacity": remaining_capacity
        }
    
    async def _execute_content_batch(
        self, batch: Dict[str, Any], ad_set_id: str, tools: Dict[str, Any]
    ) -> tuple[List[Dict], List[str]]:
        """Execute content creation with tools"""
        posts = []
        errors = []
        
        for post in batch.get("posts", []):
            try:
                # Route to appropriate tool based on post type
                # Tool execution would happen here
                posts.append(post)
            except Exception as e:
                errors.append(str(e))
        
        return posts, errors
