"""
Background Scheduler Service
APScheduler-based background job management for periodic data updates.
"""

import os
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Manages background jobs for periodic data updates.
    Uses APScheduler for async job scheduling.
    """
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def init(self):
        """Initialize the scheduler."""
        if self._initialized:
            return
        
        self.scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed jobs
                "max_instances": 1,
                "misfire_grace_time": 3600
            }
        )
        self._initialized = True
        logger.info("Background scheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        if not self._initialized:
            self.init()
        
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Background scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Background scheduler shutdown")
    
    # ============ Job Management ============
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        **kwargs
    ) -> bool:
        """
        Add a job that runs at fixed intervals.
        
        Args:
            job_id: Unique job identifier
            func: Async function to execute
            hours, minutes, seconds: Interval timing
            **kwargs: Additional arguments for the function
        """
        if not self.scheduler:
            self.init()
        
        try:
            self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
                id=job_id,
                replace_existing=True,
                kwargs=kwargs
            )
            
            self.jobs[job_id] = {
                "type": "interval",
                "interval": f"{hours}h {minutes}m {seconds}s",
                "added_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            logger.info(f"Added interval job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
            return False
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = 0,
        minute: int = 0,
        day_of_week: str = "*",
        **kwargs
    ) -> bool:
        """
        Add a job that runs on a cron schedule.
        
        Args:
            job_id: Unique job identifier
            func: Async function to execute
            hour, minute: Time to run (24h format)
            day_of_week: Cron day spec (0-6 for Mon-Sun, * for all)
        """
        if not self.scheduler:
            self.init()
        
        try:
            self.scheduler.add_job(
                func,
                trigger=CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week),
                id=job_id,
                replace_existing=True,
                kwargs=kwargs
            )
            
            self.jobs[job_id] = {
                "type": "cron",
                "schedule": f"{hour}:{minute:02d} ({day_of_week})",
                "added_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            logger.info(f"Added cron job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add cron job {job_id}: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            if self.scheduler:
                self.scheduler.remove_job(job_id)
            
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "removed"
            
            logger.info(f"Removed job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            if self.scheduler:
                self.scheduler.pause_job(job_id)
            
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "paused"
            
            return True
        except Exception:
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            if self.scheduler:
                self.scheduler.resume_job(job_id)
            
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "active"
            
            return True
        except Exception:
            return False
    
    def get_jobs(self) -> Dict[str, Dict]:
        """Get all registered jobs."""
        return self.jobs
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job."""
        return self.jobs.get(job_id)


# Singleton instance
background_scheduler = BackgroundScheduler()


# ============ Pre-defined Jobs ============

async def refresh_company_data():
    """
    Refresh research data for popular companies.
    Runs periodically to keep cache fresh.
    """
    try:
        from .research_agent import research_tool
        
        popular_companies = ["Google", "Microsoft", "Amazon", "Meta", "Apple"]
        
        for company in popular_companies:
            await research_tool.research_company(
                company_name=company,
                categories=["interview", "tech_stack"],
                max_results_per_category=3
            )
            logger.info(f"Refreshed data for {company}")
            
    except Exception as e:
        logger.error(f"Company data refresh failed: {e}")


async def cleanup_old_sessions():
    """
    Cleanup abandoned interview sessions.
    Marks old active sessions as abandoned.
    """
    try:
        from ..database import get_database
        from datetime import timedelta
        
        db = get_database()
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.interview_sessions.update_many(
            {
                "status": "active",
                "updated_at": {"$lt": cutoff}
            },
            {
                "$set": {
                    "status": "abandoned",
                    "abandoned_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Cleaned up {result.modified_count} abandoned sessions")
            
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")


async def update_trending_topics():
    """
    Update trending interview topics.
    Fetches latest trends for interview prep.
    """
    try:
        from .research_agent import research_tool
        
        trending_searches = [
            "software engineer interview 2024",
            "system design interview trends",
            "leetcode patterns popular"
        ]
        
        for search in trending_searches:
            # Just warm up the cache
            await research_tool._search_serp(search, max_results=3)
        
        logger.info("Updated trending topics")
        
    except Exception as e:
        logger.error(f"Trending topics update failed: {e}")


async def ingest_opportunities():
    """
    Ingest external opportunities (jobs, hackathons, content).
    Module 4 data ingestion.
    """
    try:
        from .opportunity_ingestion import opportunity_ingestion
        
        result = await opportunity_ingestion.ingest_all(use_mock=True)
        logger.info(f"Opportunities ingested: {result}")
        
    except Exception as e:
        logger.error(f"Opportunity ingestion failed: {e}")


def register_default_jobs():
    """Register default background jobs."""
    scheduler = background_scheduler
    
    # Initialize scheduler
    scheduler.init()
    
    # Refresh company data every 6 hours
    scheduler.add_interval_job(
        job_id="refresh_company_data",
        func=refresh_company_data,
        hours=6
    )
    
    # Cleanup old sessions daily at 3 AM UTC
    scheduler.add_cron_job(
        job_id="cleanup_sessions",
        func=cleanup_old_sessions,
        hour=3,
        minute=0
    )
    
    # Update trending topics every 12 hours
    scheduler.add_interval_job(
        job_id="update_trends",
        func=update_trending_topics,
        hours=12
    )
    
    # Ingest jobs daily at 6 AM UTC
    scheduler.add_cron_job(
        job_id="ingest_opportunities",
        func=ingest_opportunities,
        hour=6,
        minute=0
    )
    
    logger.info("Default background jobs registered")

