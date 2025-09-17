# backend/api/routes/executions.py

"""
API routes for execution data retrieval
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from backend.services.execution_data import ExecutionDataService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summaries")
async def get_execution_summaries(
    initiative_id: Optional[str] = Query(None, description="Filter by initiative ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
) -> List[Dict[str, Any]]:
    """
    Get list of execution summaries for dropdown
    
    Args:
        initiative_id: Optional filter by initiative
        limit: Maximum number of results (1-100)
        
    Returns:
        List of execution summaries
    """
    try:
        service = ExecutionDataService(initiative_id=initiative_id)
        summaries = await service.get_execution_summaries(
            initiative_id=initiative_id,
            limit=limit
        )
        return summaries
    except Exception as e:
        logger.error(f"Failed to fetch execution summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}")
async def get_execution_details(execution_id: str) -> Dict[str, Any]:
    """
    Get comprehensive details for a specific execution
    
    Args:
        execution_id: The execution UUID
        
    Returns:
        Dictionary containing all execution-related data
    """
    try:
        service = ExecutionDataService()
        details = await service.get_execution_details(execution_id)
        
        if not details or not details.get('summary'):
            raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
        
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch execution details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/summary")
async def get_execution_summary(execution_id: str) -> Dict[str, Any]:
    """
    Get summary for a specific execution
    
    Args:
        execution_id: The execution UUID
        
    Returns:
        Execution summary data
    """
    try:
        service = ExecutionDataService()
        summary = await service.get_execution_summary(execution_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
        
        return summary
    except Exception as e:
        logger.error(f"Failed to fetch execution summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/campaigns")
async def get_execution_campaigns(execution_id: str) -> List[Dict[str, Any]]:
    """Get campaigns for an execution"""
    try:
        service = ExecutionDataService()
        campaigns = await service._fetch_campaigns(execution_id)
        return campaigns
    except Exception as e:
        logger.error(f"Failed to fetch campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/ad-sets")
async def get_execution_ad_sets(execution_id: str) -> List[Dict[str, Any]]:
    """Get ad sets for an execution"""
    try:
        service = ExecutionDataService()
        ad_sets = await service._fetch_ad_sets(execution_id)
        return ad_sets
    except Exception as e:
        logger.error(f"Failed to fetch ad sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/posts")
async def get_execution_posts(execution_id: str) -> List[Dict[str, Any]]:
    """Get posts for an execution"""
    try:
        service = ExecutionDataService()
        posts = await service._fetch_posts(execution_id)
        return posts
    except Exception as e:
        logger.error(f"Failed to fetch posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/research")
async def get_execution_research(execution_id: str) -> List[Dict[str, Any]]:
    """Get research entries for an execution"""
    try:
        service = ExecutionDataService()
        research = await service._fetch_research(execution_id)
        return research
    except Exception as e:
        logger.error(f"Failed to fetch research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/media")
async def get_execution_media(execution_id: str) -> List[Dict[str, Any]]:
    """Get media files for an execution"""
    try:
        service = ExecutionDataService()
        media = await service._fetch_media_files(execution_id)
        return media
    except Exception as e:
        logger.error(f"Failed to fetch media files: {e}")
        raise HTTPException(status_code=500, detail=str(e))