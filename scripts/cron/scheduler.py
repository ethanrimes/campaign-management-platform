# scripts/cron/scheduler.py

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import job modules
from scripts.cron.orchestrator_job import run_orchestrator_job
from scripts.cron.content_creator_job import run_content_creator_job
from scripts.cron.researcher_job import run_researcher_job
from scripts.cron.metrics_collector_job import run_metrics_collector_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CampaignScheduler:
    """Main scheduler for all campaign management jobs"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        
    def initialize_jobs(self):
        """Initialize all scheduled jobs"""
        from backend.config.settings import settings
        
        # Orchestrator job
        self.scheduler.add_job(
            run_orchestrator_job,
            CronTrigger.from_crontab(settings.ORCHESTRATOR_SCHEDULE),
            id="orchestrator_job",
            name="Campaign Orchestrator",
            misfire_grace_time=300
        )
        
        # Content Creator job
        self.scheduler.add_job(
            run_content_creator_job,
            CronTrigger.from_crontab(settings.CONTENT_CREATOR_SCHEDULE),
            id="content_creator_job",
            name="Content Creator",
            misfire_grace_time=300
        )
        
        # Researcher job
        self.scheduler.add_job(
            run_researcher_job,
            CronTrigger.from_crontab(settings.RESEARCHER_SCHEDULE),
            id="researcher_job",
            name="Research Agent",
            misfire_grace_time=300
        )
        
        # Metrics Collector job
        self.scheduler.add_job(
            run_metrics_collector_job,
            CronTrigger.from_crontab(settings.METRICS_COLLECTOR_SCHEDULE),
            id="metrics_collector_job",
            name="Metrics Collector",
            misfire_grace_time=60
        )
        
        logger.info("All jobs initialized")
    
    def start(self):
        """Start the scheduler"""
        self.initialize_jobs()
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def pause_job(self, job_id: str):
        """Pause a specific job"""
        self.scheduler.pause_job(job_id)
        logger.info(f"Job {job_id} paused")
    
    def resume_job(self, job_id: str):
        """Resume a specific job"""
        self.scheduler.resume_job(job_id)
        logger.info(f"Job {job_id} resumed")


async def main():
    """Main entry point for scheduler"""
    scheduler = CampaignScheduler()
    
    try:
        scheduler.start()
        logger.info("Campaign Management Scheduler is running...")
        
        # Keep the scheduler running
        while True:
            await asyncio.sleep(60)
            
            # Log status every minute
            jobs = scheduler.get_jobs()
            logger.info(f"Active jobs: {len(jobs)}")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())