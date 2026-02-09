"""
Event Bus Module

Handles internal pub/sub events for the application.
Allows decoupling components (e.g., Auth -> Notification).
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Awaitable, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ==========================================
# Event Definitions
# ==========================================

@dataclass
class Event:
    type: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: Optional[str] = None

class EventTypes:
    # User Events
    USER_SIGNED_UP = "user.signed_up"
    PROFILE_UPDATED = "user.profile.updated"
    USER_REGISTERED = "user.registered" # Added for analytics compatibility
    
    # Job Events
    JOB_POSTED = "job.posted"
    JOB_VIEWED = "job.viewed"       # Added for analytics
    JOB_SAVED = "job.saved"         # Added for analytics
    JOB_APPLIED = "job.applied"
    JOB_APPROVED = "job.approved"
    JOB_SUSPENDED = "job.suspended"
    JOB_FLAGGED = "job.flagged"
    JOB_ESCALATED = "job.escalated" # Added for audit log
    ADMIN_ACTION_TAKEN = "admin.action_taken" # Added for audit log
    
    # Application Events
    APPLICATION_CREATED = "application.created" # Added for analytics
    APPLICATION_STAGE_CHANGED = "application.stage_changed"
    APPLICATION_WITHDRAWN = "application.withdrawn" # Added for audit log
    
    # Interview Events
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_COMPLETED = "interview.completed" # Added for analytics
    
    # Offer Events
    OFFER_EXTENDED = "offer.extended"
    OFFER_ACCEPTED = "offer.accepted"
    OFFER_DECLINED = "offer.declined"
    
    # User Events - Audit
    USER_PROFILE_UPDATED = "user.profile.updated" # Duplicate of above but consistent naming
    USER_SCORE_CHANGED = "user.score_changed"

Events = EventTypes  # Alias for backward compatibility


# ==========================================
# Event Bus
# ==========================================

class EventBus:
    """
    Central event manager.
    Supports asynchronous subscribers.
    """
    
    def __init__(self):
        # Format: { "event_type": [handler_func, handler_func] }
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self._background_tasks = set()
    
    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Register a handler for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Handler subscribed to {event_type}")

    async def publish(self, event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None, actor_id: Optional[str] = None):
        """
        Publish an event to all subscribers.
        FIRE-AND-FORGET: Runs handlers in background.
        """
        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for {event_type}")
            return
        
        event_id = str(uuid.uuid4())
        
        # Inject correlation_id if passed explicitly or exists in payload
        cid = correlation_id or payload.get("correlation_id")
        
        event = Event(
            type=event_type,
            payload=payload,
            correlation_id=cid
        )
        # Note: Event dataclass doesn't support actor_id directly as per previous steps, 
        # so we rely on payload or we should add it. 
        # For now, let's stick to the Event definition we agreed on.
        
        logger.info(f"Publishing event {event_type} [{event_id}]")
        
        # Fire handlers in background tasks
        for handler in self._subscribers[event_type]:
            task = asyncio.create_task(self._run_handler(handler, event))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _run_handler(self, handler, event):
        """Execute handler with error safety."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")

# Singleton instance
event_bus = EventBus()


# ==========================================
# Helper Functions
# ==========================================

async def publish_event(event_type: str, payload: Dict[str, Any]):
    """Helper to publish event easily."""
    await event_bus.publish(event_type, payload)

def on_event(event_type: str):
    """Decorator for easy subscription."""
    def decorator(func):
        event_bus.subscribe(event_type, func)
        return func
    return decorator
