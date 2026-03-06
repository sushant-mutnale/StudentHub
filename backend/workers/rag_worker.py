"""
RAG Background Worker

Listens for new content (Jobs, Courses) and vectorizes them.
"""

import logging
from ..events.event_bus import Events
from .worker_base import BackgroundWorker
from ..services.rag_manager import rag_manager

logger = logging.getLogger(__name__)

class RAGWorker(BackgroundWorker):
    def __init__(self):
        super().__init__(
            name="RAGWorker",
            subscribed_events=[Events.JOB_POSTED, Events.PROFILE_UPDATED]
        )
    
    async def handle_event(self, event):
        event_type = event.type
        payload = event.payload
        
        logger.info(f"RAGWorker processing {event_type}")
        
        if event_type == Events.JOB_POSTED:
            # Vectorize Job Description
            job_id = payload.get("id") or str(payload.get("_id"))
            description = payload.get("description", "")
            title = payload.get("title", "")
            
            loc_raw = payload.get("location", "")
            loc_str = loc_raw if isinstance(loc_raw, str) else loc_raw.get("city", "")
            
            if job_id and description:
                text = f"{title}\n{description}"
                success = await rag_manager.add_public_job(
                    job_id=job_id,
                    job_text=text,
                    metadata={
                        "title": title, 
                        "company": payload.get("company_name", ""),
                        "location": loc_str
                    }
                )
                if success:
                    logger.info(f"✅ Auto-vectorized job {job_id}")
                else:
                    logger.error(f"❌ Failed to vectorize job {job_id}")
                    
        elif event_type == Events.PROFILE_UPDATED:
             # Handle profile synching if needed (e.g. updating user semantic profile)
             # Future implementation
             pass

rag_worker = RAGWorker()
