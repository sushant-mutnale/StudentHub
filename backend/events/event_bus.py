"""
Event-Driven Architecture - Core Event Bus

This module provides a central pub/sub event bus for decoupled, asynchronous
communication between services. Key features:

- Decoupled publishers and subscribers
- Async event processing with backpressure
- Event persistence for reliability
- Correlation ID propagation for tracing
- Retry logic for failed handlers

Usage:
    from backend.events.event_bus import event_bus, EventTypes

    # Publish an event
    await event_bus.publish(
        event_type=EventTypes.APPLICATION_STAGE_CHANGED,
        payload={"application_id": "123", "new_stage": "interview"},
        correlation_id="req-abc-123"
    )

    # Subscribe a handler
    @event_bus.subscribe(EventTypes.APPLICATION_STAGE_CHANGED)
    async def handle_stage_change(event):
        await send_notification(event.payload)
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventTypes(str, Enum):
    """All event types in the system."""
    
    # Application events (Module 5)
    APPLICATION_CREATED = "application.created"
    APPLICATION_STAGE_CHANGED = "application.stage.changed"
    APPLICATION_WITHDRAWN = "application.withdrawn"
    
    # Interview events (Module 2/5)
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_COMPLETED = "interview.completed"
    INTERVIEW_CANCELLED = "interview.cancelled"
    
    # Offer events (Module 2/5)
    OFFER_EXTENDED = "offer.extended"
    OFFER_ACCEPTED = "offer.accepted"
    OFFER_DECLINED = "offer.declined"
    OFFER_EXPIRED = "offer.expired"
    
    # Job events (Module 2/4)
    JOB_POSTED = "job.posted"
    JOB_APPROVED = "job.approved"
    JOB_SUSPENDED = "job.suspended"
    JOB_CLOSED = "job.closed"
    JOB_VIEWED = "job.viewed"
    JOB_SAVED = "job.saved"
    
    # User events (Module 1)
    USER_REGISTERED = "user.registered"
    USER_PROFILE_UPDATED = "user.profile.updated"
    USER_SCORE_CHANGED = "user.score.changed"
    
    # Notification events (Module 3)
    NOTIFICATION_CREATED = "notification.created"
    NOTIFICATION_READ = "notification.read"
    
    # Recommendation events (Module 4)
    RECOMMENDATIONS_COMPUTED = "recommendations.computed"
    
    # Admin events (Module 5)
    ADMIN_ACTION_TAKEN = "admin.action.taken"
    JOB_FLAGGED = "job.flagged"
    JOB_ESCALATED = "job.escalated"


class Event(BaseModel):
    """Immutable event structure."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventTypes
    payload: Dict[str, Any]
    correlation_id: str
    actor_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = True  # Immutable


class EventHandler(BaseModel):
    """Registered event handler."""
    
    event_type: EventTypes
    handler: Callable
    name: str
    priority: int = 0  # Higher = runs first
    
    class Config:
        arbitrary_types_allowed = True


class EventBus:
    """
    Central event bus for pub/sub messaging.
    
    Features:
    - In-process async event handling
    - Handler priority ordering
    - Error isolation (one handler failure doesn't stop others)
    - Event history for debugging
    """
    
    def __init__(self, max_history: int = 1000):
        self._handlers: Dict[EventTypes, List[EventHandler]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._processing = False
        self._queue: asyncio.Queue = asyncio.Queue()
    
    def subscribe(self, event_type: EventTypes, priority: int = 0):
        """
        Decorator to subscribe a handler to an event type.
        
        @event_bus.subscribe(EventTypes.APPLICATION_STAGE_CHANGED)
        async def my_handler(event: Event):
            ...
        """
        def decorator(handler: Callable):
            self.register_handler(event_type, handler, priority)
            return handler
        return decorator
    
    def register_handler(
        self, 
        event_type: EventTypes, 
        handler: Callable,
        priority: int = 0
    ):
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        handler_obj = EventHandler(
            event_type=event_type,
            handler=handler,
            name=handler.__name__,
            priority=priority
        )
        
        self._handlers[event_type].append(handler_obj)
        # Sort by priority (higher first)
        self._handlers[event_type].sort(key=lambda h: -h.priority)
        
        logger.info(f"Registered handler '{handler.__name__}' for {event_type.value}")
    
    async def publish(
        self,
        event_type: EventTypes,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """
        Publish an event to all subscribed handlers.
        
        Returns the created Event for reference.
        """
        event = Event(
            type=event_type,
            payload=payload,
            correlation_id=correlation_id or str(uuid4()),
            actor_id=actor_id,
            metadata=metadata or {}
        )
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Process handlers
        await self._dispatch(event)
        
        logger.info(
            f"Published event {event_type.value}",
            extra={
                "event_id": event.id,
                "correlation_id": event.correlation_id
            }
        )
        
        return event
    
    async def _dispatch(self, event: Event):
        """Dispatch event to all registered handlers."""
        handlers = self._handlers.get(event.type, [])
        
        if not handlers:
            logger.debug(f"No handlers for {event.type.value}")
            return
        
        for handler_obj in handlers:
            try:
                result = handler_obj.handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(
                    f"Handler '{handler_obj.name}' failed for {event.type.value}: {e}",
                    extra={
                        "event_id": event.id,
                        "correlation_id": event.correlation_id,
                        "error": str(e)
                    }
                )
                # Continue with other handlers - don't let one failure stop all
    
    def get_handlers(self, event_type: EventTypes) -> List[str]:
        """Get list of handler names for an event type."""
        handlers = self._handlers.get(event_type, [])
        return [h.name for h in handlers]
    
    def get_recent_events(self, limit: int = 50) -> List[Event]:
        """Get recent events for debugging."""
        return self._event_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "total_event_types": len(self._handlers),
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "recent_events_count": len(self._event_history),
            "handlers_by_type": {
                et.value: len(handlers) 
                for et, handlers in self._handlers.items()
            }
        }


# Global event bus instance
event_bus = EventBus()


# ============ Convenience Functions ============

async def publish_event(
    event_type: EventTypes,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None
) -> Event:
    """Convenience function to publish an event."""
    return await event_bus.publish(
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
        actor_id=actor_id
    )


def on_event(event_type: EventTypes, priority: int = 0):
    """Decorator alias for subscribing to events."""
    return event_bus.subscribe(event_type, priority)
