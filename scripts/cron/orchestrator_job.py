# scripts/cron/orchestrator_job.py

import asyncio
from typing import List
from backend.db.supabase_client import DatabaseClient
from agents.orchestrator.agent import OrchestratorAgent, AgentConfig
import logging

logger = logging.getLogger(__name__)


async def run_orchestrator_job():
    """Run orchestrator job for all active initiatives"""
    logger.info("Starting orchestrator job")
    
    try:
        # Get all active initiatives
        db = DatabaseClient()
        initiatives = await db.select(
            "initiatives",
            filters={"is_active": True}
        )
        
        # Run orchestrator for each initiative
        for initiative in initiatives:
            await process_initiative_orchestration(initiative)
        
        logger.info(f"Orchestrator job completed for {len(initiatives)} initiatives")
        
    except Exception as e:
        logger.error(f"Orchestrator job failed: {e}")


async def process_initiative_orchestration(initiative: dict):
    """Process orchestration for a single initiative"""
    try:
        logger.info(f"Processing orchestration for initiative: {initiative['name']}")
        
        # Create agent config
        config = AgentConfig(
            name="Campaign Orchestrator",
            description="Plans and manages campaigns",
            tenant_id=initiative["tenant_id"],
            initiative_id=initiative["id"],
            model_provider=initiative.get("model_provider", "openai")
        )
        
        # Create and run agent
        agent = OrchestratorAgent(config)
        result = await agent.execute({
            "initiative_id": initiative["id"],
            "trigger": "scheduled"
        })
        
        if result.success:
            # Save the campaign hierarchy
            await agent.save_hierarchy(result.data)
            logger.info(f"Orchestration successful for {initiative['name']}")
        else:
            logger.error(f"Orchestration failed for {initiative['name']}: {result.errors}")
            
    except Exception as e:
        logger.error(f"Error processing initiative {initiative.get('name', 'unknown')}: {e}")