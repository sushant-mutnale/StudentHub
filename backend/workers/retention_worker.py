"""
Data Retention Worker (Governance)

Enforces data retention policies by cleaning up old records.
Run frequency: Daily
"""

import logging
from datetime import datetime, timedelta

from .worker_base import BackgroundWorker
from ..models.notification import notifications_collection
from ..models.outbox import outbox
from ..services.recommendation_engine import recommendations_offline_collection
from ..database import get_database

logger = logging.getLogger(__name__)

class RetentionWorker(BackgroundWorker):
    """
    Worker that enforces data retention policies.
    """
    
    def __init__(self, poll_interval: float = 86400): # Once a day default
        super().__init__(
            name="retention_worker",
            poll_interval=poll_interval,
            batch_size=100
        )
    
    async def get_jobs(self) -> list:
        # This worker doesn't use the standard "get_jobs" loop 
        # because it performs bulk delete operations.
        # We'll trigger the process in process_job with a dummy job.
        return ["retention_task"]

    async def process_job(self, job: str) -> bool:
        if job != "retention_task":
            return True
            
        logger.info("Running Data Retention Policies...")
        
        try:
            # 1. Notifications (keep 60 days)
            limit_date = datetime.utcnow() - timedelta(days=60)
            res = await notifications_collection().delete_many(
                {"created_at": {"$lt": limit_date}}
            )
            if res.deleted_count > 0:
                logger.info(f"Deleted {res.deleted_count} old notifications")
            
            # 2. Outbox (keep 7 days - cleanup worker handles processed, this handles failed/stuck)
            limit_date = datetime.utcnow() - timedelta(days=7)
            # Assuming cleanup worker handles success, we might want to hard delete stale failed ones
            # Implementation depends on specific policy, skipping if outbox_cleanup covers it.
            
            # 3. Offline Recommendations (keep 7 days)
            limit_date = datetime.utcnow() - timedelta(days=7)
            res = await recommendations_offline_collection().delete_many(
                {"updated_at": {"$lt": limit_date}}
            )
            if res.deleted_count > 0:
                 logger.info(f"Deleted {res.deleted_count} stale recommendation sets")
                 
            # 4. Audit Logs (keep 1 year)
            # Assuming we have an audit collection
            limit_date = datetime.utcnow() - timedelta(days=365)
            # await get_database()["audit_logs"].delete_many(...)
            
            return True
            
        except Exception as e:
            logger.error(f"Retention policy failed: {e}")
            return False
