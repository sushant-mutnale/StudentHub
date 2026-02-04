"""
Activity Feed Service - Unified activity timeline per application.

Provides a central view of all events:
- Stage changes
- Interview events (scheduled, completed)
- Offer events (extended, accepted, rejected)
- Messages (linked from thread)
- Scorecard submissions
- Recruiter notes
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from ..database import get_database


def activity_events_collection():
    return get_database()["activity_events"]


# Event types
EVENT_STAGE_CHANGE = "stage_change"
EVENT_INTERVIEW_SCHEDULED = "interview_scheduled"
EVENT_INTERVIEW_COMPLETED = "interview_completed"
EVENT_INTERVIEW_CANCELLED = "interview_cancelled"
EVENT_OFFER_EXTENDED = "offer_extended"
EVENT_OFFER_ACCEPTED = "offer_accepted"
EVENT_OFFER_REJECTED = "offer_rejected"
EVENT_MESSAGE = "message"
EVENT_SCORECARD = "scorecard"
EVENT_NOTE = "note"
EVENT_TAG = "tag"
EVENT_APPLICATION = "application"


async def log_activity_event(
    application_id: str,
    event_type: str,
    actor_id: str,
    title: str,
    description: Optional[str] = None,
    data: Optional[Dict] = None,
    visible_to: Optional[List[str]] = None
) -> dict:
    """Log an activity event to the application timeline."""
    if visible_to is None:
        visible_to = ["recruiter", "student"]
    
    now = datetime.utcnow()
    event = {
        "application_id": ObjectId(application_id),
        "event_type": event_type,
        "actor_id": ObjectId(actor_id),
        "title": title,
        "description": description,
        "data": data or {},
        "visible_to": visible_to,
        "timestamp": now
    }
    
    result = await activity_events_collection().insert_one(event)
    event["_id"] = result.inserted_id
    return event


async def get_activity_feed(
    application_id: str,
    include_private: bool = True,
    limit: int = 50
) -> List[dict]:
    """Get the activity feed for an application."""
    query: Dict[str, Any] = {"application_id": ObjectId(application_id)}
    
    if not include_private:
        # Only show events visible to students
        query["visible_to"] = "student"
    
    cursor = activity_events_collection().find(query).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_activity_count(application_id: str) -> int:
    """Get the count of activity events for an application."""
    return await activity_events_collection().count_documents({
        "application_id": ObjectId(application_id)
    })


# Convenience functions for common events
async def log_application_created(application_id: str, student_id: str, job_title: str):
    """Log when application is created."""
    return await log_activity_event(
        application_id=application_id,
        event_type=EVENT_APPLICATION,
        actor_id=student_id,
        title="Application Submitted",
        description=f"Applied for {job_title}",
        visible_to=["recruiter", "student"]
    )


async def log_stage_change(
    application_id: str,
    actor_id: str,
    from_stage: str,
    to_stage: str,
    reason: Optional[str] = None,
    visible_to_student: bool = True
):
    """Log a stage change event."""
    visibility = ["recruiter", "student"] if visible_to_student else ["recruiter"]
    return await log_activity_event(
        application_id=application_id,
        event_type=EVENT_STAGE_CHANGE,
        actor_id=actor_id,
        title=f"Moved to {to_stage}",
        description=reason,
        data={"from_stage": from_stage, "to_stage": to_stage},
        visible_to=visibility
    )


async def log_interview_event(
    application_id: str,
    actor_id: str,
    interview_id: str,
    event_type: str,
    title: str,
    scheduled_time: Optional[datetime] = None
):
    """Log an interview-related event."""
    data = {"interview_id": interview_id}
    if scheduled_time:
        data["scheduled_time"] = scheduled_time.isoformat()
    
    return await log_activity_event(
        application_id=application_id,
        event_type=event_type,
        actor_id=actor_id,
        title=title,
        data=data,
        visible_to=["recruiter", "student"]
    )


async def log_offer_event(
    application_id: str,
    actor_id: str,
    offer_id: str,
    event_type: str,
    title: str,
    package: Optional[str] = None
):
    """Log an offer-related event."""
    data = {"offer_id": offer_id}
    if package:
        data["package"] = package
    
    return await log_activity_event(
        application_id=application_id,
        event_type=event_type,
        actor_id=actor_id,
        title=title,
        data=data,
        visible_to=["recruiter", "student"]
    )


async def log_scorecard_submitted(
    application_id: str,
    evaluator_id: str,
    scorecard_id: str,
    template_name: str,
    overall_score: float,
    decision: str
):
    """Log when a scorecard is submitted."""
    return await log_activity_event(
        application_id=application_id,
        event_type=EVENT_SCORECARD,
        actor_id=evaluator_id,
        title=f"Scorecard Submitted: {template_name}",
        description=f"Score: {overall_score:.1f}/5, Decision: {decision.title()}",
        data={
            "scorecard_id": scorecard_id,
            "overall_score": overall_score,
            "decision": decision
        },
        visible_to=["recruiter"]  # Scorecards not visible to students
    )


async def log_note_added(
    application_id: str,
    author_id: str,
    note_preview: str,
    is_private: bool = True
):
    """Log when a note is added."""
    visibility = ["recruiter"] if is_private else ["recruiter", "student"]
    return await log_activity_event(
        application_id=application_id,
        event_type=EVENT_NOTE,
        actor_id=author_id,
        title="Note Added",
        description=note_preview[:100] + "..." if len(note_preview) > 100 else note_preview,
        visible_to=visibility
    )


async def ensure_activity_indexes():
    """Create indexes for activity events."""
    col = activity_events_collection()
    await col.create_index("application_id")
    await col.create_index([("application_id", 1), ("timestamp", -1)])
    await col.create_index("timestamp")
    await col.create_index("event_type")
