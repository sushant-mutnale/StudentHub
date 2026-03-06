"""
Moderation Event Handler

Listens for content creation events and triggers automated risk analysis.
"""

import logging
from . import register_handler
from ..event_bus import Event, EventTypes
from ..services.moderation_service import moderation_service

logger = logging.getLogger(__name__)

@register_handler(EventTypes.JOB_POSTED)
async def handle_new_job_posting(event: Event):
    """
    Analyze new job postings for prohibited content.
    """
    job_id = event.payload.get("job_id")
    job_title = event.payload.get("title", "")
    job_desc = event.payload.get("description", "")
    
    if not job_id:
        return

    logger.info(f"Scanning job {job_id} for risk...")
    
    # Analyze text
    full_text = f"{job_title} {job_desc}"
    analysis = moderation_service.analyze_text(full_text)
    
    # Flag if needed
    if analysis["score"] > 0:
        logger.warning(f"Risk detected in job {job_id}: {analysis['level']} ({analysis['score']})")
        await moderation_service.flag_content(
            content_type="job",
            content_id=job_id,
            analysis=analysis
        )
    else:
        logger.info(f"Job {job_id} passed moderation.")
