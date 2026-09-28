"""
RAG Vectorization Event Handler

Asynchronously vectorizes jobs and user resumes when relevant events are published.
This decouples the embedding/Pinecone upsert from the synchronous HTTP request
path, improving latency for job posting and resume upload endpoints.
"""

import logging
from ..event_bus import event_bus, Event, EventTypes

logger = logging.getLogger(__name__)


async def _vectorize_job(event: Event):
    """Upsert a job into the public RAG namespace when it is posted."""
    try:
        from ...services.rag_manager import rag_manager

        payload = event.payload
        job_id = payload.get("id")
        if not job_id:
            return

        parts = [
            payload.get("title", ""),
            payload.get("description", ""),
            payload.get("company_name", ""),
            payload.get("location", ""),
        ]
        text = " | ".join(p for p in parts if p)
        if not text.strip():
            return

        await rag_manager.add_public_job(
            job_id=job_id,
            job_text=text,
            metadata={
                "company_name": payload.get("company_name"),
                "location": payload.get("location"),
            },
        )
        logger.info("Async RAG vectorization: job %s vectorized", job_id)
    except Exception as e:
        logger.error("Async RAG vectorization failed for job %s: %s", event.payload.get("id"), e)


async def _vectorize_user_resume(event: Event):
    """Upsert user resume into the private RAG namespace on profile updates."""
    try:
        from ...services.rag_manager import rag_manager

        payload = event.payload
        user_id = payload.get("id") or payload.get("user_id")
        resume_text = payload.get("resume_text") or payload.get("bio")
        if not user_id or not resume_text:
            return

        await rag_manager.add_user_resume(user_id=user_id, resume_text=resume_text)
        logger.info("Async RAG vectorization: resume for user %s vectorized", user_id)
    except Exception as e:
        logger.error("Async RAG vectorization failed for user %s: %s", event.payload.get("user_id"), e)


def register_rag_handlers():
    """Subscribe RAG vectorization handlers to relevant domain events."""
    event_bus.subscribe(EventTypes.JOB_POSTED, _vectorize_job)
    event_bus.subscribe(EventTypes.OPPORTUNITY_CREATED, _vectorize_job)
    event_bus.subscribe(EventTypes.USER_PROFILE_UPDATED, _vectorize_user_resume)
    logger.info("RAG vectorization event handlers registered")
