# backend/services/execution_data.py

"""
Service for fetching all data related to a workflow execution.
Consolidates data from multiple tables based on execution_id.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from backend.db.supabase_client import DatabaseClient
from backend.db.models.execution_log import ExecutionLogs
from backend.db.models.campaign import Campaigns
from backend.db.models.ad_set import AdSets
from backend.db.models.post import Posts
from backend.db.models.research import Research
from backend.db.models.media_file import MediaFiles

logger = logging.getLogger(__name__)


class ExecutionDataService:
    """Service for fetching comprehensive execution data"""
    
    def __init__(self, initiative_id: Optional[str] = None):
        """
        Initialize the service
        
        Args:
            initiative_id: Optional initiative ID for RLS
        """
        self.db = DatabaseClient(initiative_id=initiative_id)
    
    async def get_execution_summary(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution summary from the execution_logs table
        
        Args:
            execution_id: The execution UUID
            
        Returns:
            Execution summary data or None if not found
        """
        try:
            logger.info(f"Fetching execution summary for: {execution_id}")
            
            # Fetch from execution_logs
            logs = await self.db.select(
                "execution_logs",
                filters={"execution_id": execution_id},
                limit=1
            )
            
            if not logs:
                logger.warning(f"No execution log found for: {execution_id}")
                return None
            
            log = logs[0]
            
            # Calculate duration
            duration_seconds = None
            if log.get('started_at'):
                started = datetime.fromisoformat(log['started_at'].replace('Z', '+00:00'))
                completed = datetime.fromisoformat(log['completed_at'].replace('Z', '+00:00')) if log.get('completed_at') else datetime.now()
                duration_seconds = (completed - started).total_seconds()
            
            # Get counts
            campaigns_count = await self._count_records("campaigns", execution_id)
            ad_sets_count = await self._count_records("ad_sets", execution_id)
            posts_count = await self._count_records("posts", execution_id)
            research_count = await self._count_records("research", execution_id)
            media_count = await self._count_records("media_files", execution_id)
            
            return {
                "execution_id": execution_id,
                "initiative_id": log.get('initiative_id'),
                "workflow_type": log.get('workflow_type', 'unknown'),
                "status": log.get('status', 'unknown'),
                "started_at": log.get('started_at'),
                "completed_at": log.get('completed_at'),
                "duration_seconds": duration_seconds,
                "campaigns_created": campaigns_count,
                "ad_sets_created": ad_sets_count,
                "posts_created": posts_count,
                "research_entries": research_count,
                "media_files_created": media_count,
                "steps_completed": log.get('steps_completed', []),
                "steps_failed": log.get('steps_failed', []),
                "metadata": log.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch execution summary: {e}")
            return None
    
    async def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """
        Fetch all data related to an execution
        
        Args:
            execution_id: The execution UUID
            
        Returns:
            Dictionary containing all execution-related data
        """
        try:
            logger.info(f"Fetching complete execution details for: {execution_id}")
            
            # Get summary first
            summary = await self.get_execution_summary(execution_id)
            if not summary:
                raise ValueError(f"Execution not found: {execution_id}")
            
            # Set initiative context if we have it
            if summary.get('initiative_id') and not self.db.initiative_id:
                self.db = DatabaseClient(initiative_id=summary['initiative_id'])
            
            # Fetch all related data in parallel (simulated with sequential calls)
            campaigns = await self._fetch_campaigns(execution_id)
            ad_sets = await self._fetch_ad_sets(execution_id)
            posts = await self._fetch_posts(execution_id)
            research = await self._fetch_research(execution_id)
            media_files = await self._fetch_media_files(execution_id)
            
            # Fetch logs for timeline
            logs = await self._fetch_execution_logs(execution_id)
            
            result = {
                "summary": summary,
                "campaigns": campaigns,
                "adSets": ad_sets,  # Use camelCase for frontend compatibility
                "posts": posts,
                "research": research,
                "mediaFiles": media_files,  # Use camelCase for frontend compatibility
                "logs": logs
            }
            
            logger.info(f"Successfully fetched execution details: {len(campaigns)} campaigns, "
                       f"{len(ad_sets)} ad sets, {len(posts)} posts, "
                       f"{len(research)} research entries, {len(media_files)} media files")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch execution details: {e}")
            raise
    
    async def get_execution_summaries(self, initiative_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of execution summaries for dropdown
        
        Args:
            initiative_id: Optional filter by initiative
            limit: Maximum number of results
            
        Returns:
            List of execution summaries
        """
        try:
            # Use raw client to access the view
            client = self.db.raw_client()
            
            query = client.table("execution_summary").select("*").order(
                "started_at", desc=True
            ).limit(limit)
            
            if initiative_id:
                query = query.eq("initiative_id", initiative_id)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to fetch execution summaries: {e}")
            return []
    
    async def _count_records(self, table: str, execution_id: str) -> int:
        """Count records in a table for an execution"""
        try:
            records = await self.db.select(
                table,
                filters={"execution_id": execution_id},
                columns="id"
            )
            return len(records)
        except Exception as e:
            logger.warning(f"Failed to count {table} records: {e}")
            return 0
    
    async def _fetch_campaigns(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch campaigns for an execution"""
        try:
            return await self.db.select(
                "campaigns",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch campaigns: {e}")
            return []
    
    async def _fetch_ad_sets(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch ad sets for an execution"""
        try:
            return await self.db.select(
                "ad_sets",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch ad sets: {e}")
            return []
    
    async def _fetch_posts(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch posts for an execution"""
        try:
            return await self.db.select(
                "posts",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch posts: {e}")
            return []
    
    async def _fetch_research(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch research entries for an execution"""
        try:
            return await self.db.select(
                "research",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch research: {e}")
            return []
    
    async def _fetch_media_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch media files for an execution"""
        try:
            return await self.db.select(
                "media_files",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch media files: {e}")
            return []
    
    async def _fetch_execution_logs(self, execution_id: str) -> List[Dict[str, Any]]:
        """Fetch execution logs for timeline"""
        try:
            return await self.db.select(
                "execution_logs",
                filters={"execution_id": execution_id}
            )
        except Exception as e:
            logger.error(f"Failed to fetch execution logs: {e}")
            return []