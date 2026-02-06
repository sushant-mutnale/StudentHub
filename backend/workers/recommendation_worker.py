"""
Recommendation Background Worker

Periodically re-computes recommendations for active students and stores them
in the offline cache (Cold Storage) for fast retrieval.
"""

import logging
from typing import List

from .worker_base import BackgroundWorker
from ..services.recommendation_engine import recommendation_engine
from ..models.user import users_collection

logger = logging.getLogger(__name__)

class RecommendationWorker(BackgroundWorker):
    """
    Worker that computes recommendations for students.
    Runs every 24 hours (or configurable) for each student.
    """
    
    def __init__(self, poll_interval: float = 300, batch_size: int = 10):
        # Poll interval can be shorter to pick up new batches, 
        # but the logic should ensure we don't re-compute too often per student.
        super().__init__(
            name="recommendation_worker",
            poll_interval=poll_interval,
            batch_size=batch_size
        )
    
    async def get_jobs(self) -> List[str]:
        """
        Get list of students who need recommendation updates.
        Strategy: Find students with no offline recs OR old offline recs.
        """
        from datetime import datetime, timedelta
        
        # Threshold: re-compute if older than 24 hours
        threshold = datetime.utcnow() - timedelta(hours=24)
        
        # This is a simplification. Ideally, we query the offline collection 
        # to find old entries, OR query users and left-join.
        # For MongoDB, we can iterate active students and check if they need updates.
        # Better: Query users who have logged in recently (active)
        
        active_threshold = datetime.utcnow() - timedelta(days=7)
        
        # Get active students
        cursor = users_collection().find(
            {
                "role": "student",
                "last_login": {"$gte": active_threshold}
            },
            projection={"_id": 1}
        ).limit(self.batch_size)
        
        # In a real system, we'd need a way to paginate through all of them 
        # without repeating the same ones immediately. 
        # A "next_recommendation_update" field on the user or a separate task queue is best.
        # Here we will just pick a few random ones or use a simple marker if possible.
        # For MVP, let's just return a few IDs and let process_job handle the "do we actually need to update" check.
        
        students = await cursor.to_list(length=None)
        return [str(s["_id"]) for s in students]

    async def process_job(self, student_id: str) -> bool:
        """
        Compute and store recommendations for a single student.
        """
        # Check if we really need to update (avoid double work if our query was loose)
        from ..services.recommendation_engine import recommendations_offline_collection
        from datetime import datetime, timedelta
        
        cached = await recommendations_offline_collection().find_one(
            {"student_id": student_id, "type": "jobs"}
        )
        
        if cached:
            if (datetime.utcnow() - cached["updated_at"]).total_seconds() < 86400:
                # Still fresh enough, skip
                return True
        
        logger.info(f"Updating recommendations for student {student_id}")
        await recommendation_engine.compute_and_store_recommendations(student_id)
        return True
