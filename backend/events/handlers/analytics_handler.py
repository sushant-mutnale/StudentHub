"""
Analytics Event Handler

Tracks user actions for funnel analysis and product metrics.
Events are stored in an analytics collection for later aggregation.

Funnels tracked:
- Job Discovery: view → save → apply
- Hiring Funnel: apply → interview → offer → hire
- Recruiter Funnel: post → approve → applications → interviews → hires
"""

import logging
from datetime import datetime
from typing import Dict, Any

from ..event_bus import event_bus, Event, EventTypes

logger = logging.getLogger(__name__)


# Events to track for analytics
TRACKED_EVENTS = [
    EventTypes.JOB_VIEWED,
    EventTypes.JOB_SAVED,
    EventTypes.APPLICATION_CREATED,
    EventTypes.APPLICATION_STAGE_CHANGED,
    EventTypes.INTERVIEW_SCHEDULED,
    EventTypes.INTERVIEW_COMPLETED,
    EventTypes.OFFER_EXTENDED,
    EventTypes.OFFER_ACCEPTED,
    EventTypes.OFFER_DECLINED,
    EventTypes.JOB_POSTED,
    EventTypes.JOB_APPROVED,
    EventTypes.USER_REGISTERED,
]


async def track_analytics_event(event: Event):
    """
    Store event in analytics collection for funnel analysis.
    
    Schema:
    - event_type: str
    - user_id: str (actor)
    - resource_type: str (job, application, etc.)
    - resource_id: str
    - metadata: dict
    - timestamp: datetime
    - correlation_id: str
    """
    from ...database import get_database
    
    payload = event.payload
    
    # Determine resource type from event
    resource_type = "unknown"
    resource_id = None
    
    if "job_id" in payload:
        resource_type = "job"
        resource_id = payload["job_id"]
    elif "application_id" in payload:
        resource_type = "application"
        resource_id = payload["application_id"]
    elif "interview_id" in payload:
        resource_type = "interview"
        resource_id = payload["interview_id"]
    elif "offer_id" in payload:
        resource_type = "offer"
        resource_id = payload["offer_id"]
    
    analytics_event = {
        "event_type": str(event.type),
        "user_id": payload.get("user_id") or payload.get("student_id"),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "job_id": payload.get("job_id"),
        "company_id": payload.get("company_id"),
        "source": payload.get("source", "internal"),
        "metadata": {
            k: v for k, v in payload.items() 
            if k not in ["job_id", "user_id", "student_id", "company_id"]
        },
        "timestamp": event.timestamp,
        "correlation_id": event.correlation_id
    }
    
    try:
        db = get_database()
        await db.analytics_events.insert_one(analytics_event)
        logger.debug(f"Tracked analytics event: {event.type}")
    except Exception as e:
        logger.error(f"Failed to track analytics event: {e}")



async def get_funnel_metrics(job_id: str) -> Dict[str, int]:
    """
    Get funnel metrics for a specific job.
    
    Returns counts for: views → saves → applies → interviews → offers → hires
    """
    from ...database import get_database
    db = get_database()
    
    pipeline = [
        {"$match": {"job_id": job_id}},
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.analytics_events.aggregate(pipeline).to_list(None)
    
    funnel = {
        "views": 0,
        "saves": 0,
        "applications": 0,
        "interviews": 0,
        "offers": 0,
        "hires": 0
    }
    
    mapping = {
        "job.viewed": "views",
        "job.saved": "saves",
        "application.created": "applications",
        "interview.scheduled": "interviews",
        "offer.extended": "offers",
        "offer.accepted": "hires"
    }
    
    for result in results:
        event_type = result["_id"]
        if event_type in mapping:
            funnel[mapping[event_type]] = result["count"]
    
    return funnel


async def get_conversion_rates(job_id: str) -> Dict[str, float]:
    """Calculate conversion rates between funnel stages."""
    funnel = await get_funnel_metrics(job_id)
    
    rates = {}
    
    if funnel["views"] > 0:
        rates["view_to_apply"] = round(funnel["applications"] / funnel["views"] * 100, 2)
    
    if funnel["applications"] > 0:
        rates["apply_to_interview"] = round(funnel["interviews"] / funnel["applications"] * 100, 2)
    
    if funnel["interviews"] > 0:
        rates["interview_to_offer"] = round(funnel["offers"] / funnel["interviews"] * 100, 2)
    
    if funnel["offers"] > 0:
        rates["offer_to_hire"] = round(funnel["hires"] / funnel["offers"] * 100, 2)
    
    return rates


def register_analytics_handlers():
    """Register analytics handlers for all tracked events."""
    
    for event_type in TRACKED_EVENTS:
        event_bus.subscribe(
            event_type,
            track_analytics_event
        )
    
    logger.info(f"Registered analytics handlers for {len(TRACKED_EVENTS)} event types")
