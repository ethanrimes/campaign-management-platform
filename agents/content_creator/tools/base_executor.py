# agents/content_creator/tools/base_executor.py

"""
Base executor for deterministic content posting.
Replaces LangChain tools with service-based execution.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PostingStatus(str, Enum):
    """Status of posting operation"""
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class PostingResult:
    """Result of a posting operation"""
    success: bool
    post_id: Optional[str] = None
    platform_post_id: Optional[str] = None
    platform_url: Optional[str] = None
    platform: Optional[str] = None
    status: PostingStatus = PostingStatus.PENDING
    error_message: Optional[str] = None
    media_urls: List[str] = None
    execution_time_seconds: Optional[float] = None
    
    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []


class BaseExecutor:
    """Base class for content posting executors"""
    
    def __init__(self, initiative_id: str, execution_id: Optional[str] = None):
        self.initiative_id = initiative_id
        self.execution_id = execution_id
        self.execution_step = "Content Creation"
    
    async def execute(self, post_data: Dict[str, Any]) -> PostingResult:
        """Execute posting operation"""
        raise NotImplementedError("Subclasses must implement execute()")
    
    def _log_start(self, operation: str, details: Dict[str, Any] = None):
        """Log operation start"""
        log_msg = f"🚀 Starting {operation}"
        if details:
            log_msg += f" | Details: {details}"
        logger.info(log_msg)
        logger.info("=" * 70)
    
    def _log_end(self, operation: str, success: bool, details: Dict[str, Any] = None):
        """Log operation end"""
        status_icon = "✅" if success else "❌"
        log_msg = f"{status_icon} Completed {operation} | Success: {success}"
        if details:
            log_msg += f" | Details: {details}"
        logger.info(log_msg)
        logger.info("=" * 70)