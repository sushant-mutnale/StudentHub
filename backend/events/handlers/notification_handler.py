"""
Notification Event Handler

Automatically creates notifications when relevant events occur.
This decouples notification logic from business logic.
"""

import logging
from typing import Dict, Any

from ..event_bus import event_bus, Event, EventTypes

logger = logging.getLogger(__name__)


# Notification templates by event type
NOTIFICATION_TEMPLATES = {
    EventTypes.APPLICATION_STAGE_CHANGED: {
        "title": "Application Update",
        "template": "Your application has moved to the {new_stage} stage",
        "type": "application"
    },
    EventTypes.INTERVIEW_SCHEDULED: {
        "title": "Interview Scheduled",
        "template": "You have an interview scheduled for {date} at {time}",
        "type": "interview"
    },
    EventTypes.OFFER_EXTENDED: {
        "title": "🎉 Offer Received!",
        "template": "Congratulations! You've received an offer from {company_name}",
        "type": "offer"
    },
    EventTypes.OFFER_ACCEPTED: {
        "title": "Offer Accepted",
        "template": "Candidate has accepted the offer for {job_title}",
        "type": "offer"
    },
    EventTypes.JOB_APPROVED: {
        "title": "Job Posting Approved",
        "template": "Your job posting '{job_title}' has been approved and is now live",
        "type": "job"
    },
    EventTypes.JOB_SUSPENDED: {
        "title": "Job Posting Suspended",
        "template": "Your job posting '{job_title}' has been suspended: {reason}",
        "type": "job"
    },
    EventTypes.JOB_FLAGGED: {
        "title": "Job Posting Flagged",
        "template": "Job posting '{job_title}' requires review",
        "type": "admin"
    }
}


async def handle_application_stage_changed(event: Event):
    """Create notification when application stage changes."""
    payload = event.payload
    template = NOTIFICATION_TEMPLATES.get(event.type)
    
    if not template:
        return
    
    # Import here to avoid circular dependency
    from ...database import get_database
    
    notification = {
        "user_id": payload.get("student_id"),
        "type": template["type"],
        "title": template["title"],
        "message": template["template"].format(**payload),
        "related_id": payload.get("application_id"),
        "read": False,
        "correlation_id": event.correlation_id,
        "created_at": event.timestamp
    }
    
    try:
        db = get_database()
        await db.notifications.insert_one(notification)
        logger.info(
            f"Created notification for {event.type.value}",
            extra={"correlation_id": event.correlation_id}
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")


async def handle_interview_scheduled(event: Event):
    """Notify student and recruiter about scheduled interview."""
    payload = event.payload
    
    from ...database import get_database
    db = get_database()
    
    # Notify student
    student_notification = {
        "user_id": payload.get("student_id"),
        "type": "interview",
        "title": "Interview Scheduled",
        "message": f"Interview scheduled for {payload.get('date', 'upcoming date')}",
        "related_id": payload.get("interview_id"),
        "read": False,
        "correlation_id": event.correlation_id
    }
    
    # Notify recruiter
    recruiter_notification = {
        "user_id": payload.get("recruiter_id"),
        "type": "interview",
        "title": "Interview Confirmed",
        "message": f"Interview with {payload.get('student_name', 'candidate')} confirmed",
        "related_id": payload.get("interview_id"),
        "read": False,
        "correlation_id": event.correlation_id
    }
    
    try:
        await db.notifications.insert_many([student_notification, recruiter_notification])
    except Exception as e:
        logger.error(f"Failed to create interview notifications: {e}")


async def handle_offer_extended(event: Event):
    """Notify student about job offer."""
    payload = event.payload
    template = NOTIFICATION_TEMPLATES[EventTypes.OFFER_EXTENDED]
    
    from ...database import get_database
    db = get_database()
    
    notification = {
        "user_id": payload.get("student_id"),
        "type": "offer",
        "title": template["title"],
        "message": template["template"].format(
            company_name=payload.get("company_name", "a company")
        ),
        "related_id": payload.get("offer_id"),
        "read": False,
        "priority": "high",
        "correlation_id": event.correlation_id
    }
    
    try:
        await db.notifications.insert_one(notification)
    except Exception as e:
        logger.error(f"Failed to create offer notification: {e}")


async def handle_job_status_change(event: Event):
    """Notify recruiter about job approval/suspension."""
    payload = event.payload
    template = NOTIFICATION_TEMPLATES.get(event.type)
    
    if not template:
        return
    
    from ...database import get_database
    db = get_database()
    
    notification = {
        "user_id": payload.get("recruiter_id"),
        "type": "job",
        "title": template["title"],
        "message": template["template"].format(**payload),
        "related_id": payload.get("job_id"),
        "read": False,
        "correlation_id": event.correlation_id
    }
    
    try:
        await db.notifications.insert_one(notification)
    except Exception as e:
        logger.error(f"Failed to create job notification: {e}")


def register_notification_handlers():
    """Register all notification event handlers."""
    
    event_bus.register_handler(
        EventTypes.APPLICATION_STAGE_CHANGED,
        handle_application_stage_changed,
        priority=10
    )
    
    event_bus.register_handler(
        EventTypes.INTERVIEW_SCHEDULED,
        handle_interview_scheduled,
        priority=10
    )
    
    event_bus.register_handler(
        EventTypes.OFFER_EXTENDED,
        handle_offer_extended,
        priority=10
    )
    
    event_bus.register_handler(
        EventTypes.JOB_APPROVED,
        handle_job_status_change,
        priority=10
    )
    
    event_bus.register_handler(
        EventTypes.JOB_SUSPENDED,
        handle_job_status_change,
        priority=10
    )
    
    logger.info("Registered notification event handlers")
