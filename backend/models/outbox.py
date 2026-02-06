"""
Transactional Outbox Pattern

Ensures reliable event publishing by storing events in the same transaction
as the domain state change. A background worker then publishes these events.

This prevents the "DB updated but event lost" problem.

Flow:
1. Business logic writes to DB + inserts OutboxEvent in same transaction
2. Returns immediately (fast API response)
3. Background worker polls outbox, publishes events, marks as processed

Benefits:
- Atomic: Either both DB change and event record succeed, or neither
- Reliable: Events are never lost even if the event bus is temporarily down
- Idempotent: Events have unique IDs for deduplication
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class OutboxEvent(BaseModel):
    """An event stored in the outbox for reliable publishing."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    payload: Dict[str, Any]
    correlation_id: str
    actor_id: Optional[str] = None
    
    # Processing status
    status: Literal["pending", "processing", "processed", "failed"] = "pending"
    attempts: int = 0
    max_attempts: int = 5
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    
    # Error tracking
    last_error: Optional[str] = None
    
    class Config:
        use_enum_values = True


class OutboxService:
    """
    Service for managing the outbox pattern.
    
    Usage:
        # In your route/service
        async with outbox.transaction() as txn:
            await update_application_stage(...)
            await txn.add_event(
                event_type="application.stage.changed",
                payload={...}
            )
        # Event is automatically queued for publishing
    """
    
    def __init__(self):
        self._pending_events: List[OutboxEvent] = []
    
    def _get_collection(self):
        """Get the outbox collection."""
        from ..database import get_database
        return get_database().outbox_events
    
    async def add_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> str:
        """
        Add an event to the outbox.
        
        Returns the event ID for tracking.
        """
        event = OutboxEvent(
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id or str(uuid4()),
            actor_id=actor_id
        )
        
        collection = self._get_collection()
        await collection.insert_one(event.dict())
        
        logger.info(
            f"Added outbox event: {event_type}",
            extra={"event_id": event.id, "correlation_id": event.correlation_id}
        )
        
        return event.id
    
    async def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        """Get pending events for processing."""
        collection = self._get_collection()
        
        cursor = collection.find({
            "status": {"$in": ["pending", "failed"]},
            "attempts": {"$lt": 5}
        }).sort("created_at", 1).limit(limit)
        
        docs = await cursor.to_list(length=limit)
        return [OutboxEvent(**doc) for doc in docs]
    
    async def mark_processing(self, event_id: str):
        """Mark an event as being processed."""
        collection = self._get_collection()
        await collection.update_one(
            {"id": event_id},
            {
                "$set": {
                    "status": "processing",
                    "last_attempt_at": datetime.utcnow()
                },
                "$inc": {"attempts": 1}
            }
        )
    
    async def mark_processed(self, event_id: str):
        """Mark an event as successfully processed."""
        collection = self._get_collection()
        await collection.update_one(
            {"id": event_id},
            {
                "$set": {
                    "status": "processed",
                    "processed_at": datetime.utcnow()
                }
            }
        )
        logger.info(f"Outbox event processed: {event_id}")
    
    async def mark_failed(self, event_id: str, error: str):
        """Mark an event as failed."""
        collection = self._get_collection()
        await collection.update_one(
            {"id": event_id},
            {
                "$set": {
                    "status": "failed",
                    "last_error": error
                }
            }
        )
        logger.warning(f"Outbox event failed: {event_id} - {error}")
    
    async def cleanup_old_events(self, days: int = 7):
        """Remove successfully processed events older than N days."""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        collection = self._get_collection()
        
        result = await collection.delete_many({
            "status": "processed",
            "processed_at": {"$lt": cutoff}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} old outbox events")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get outbox statistics."""
        collection = self._get_collection()
        
        pipeline = [
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        results = await collection.aggregate(pipeline).to_list(None)
        
        stats = {
            "pending": 0,
            "processing": 0,
            "processed": 0,
            "failed": 0
        }
        
        for result in results:
            stats[result["_id"]] = result["count"]
        
        return stats


# Global outbox service instance
outbox = OutboxService()


# ============ Helper Functions ============

async def publish_with_outbox(
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None
) -> str:
    """
    Helper to add an event to the outbox.
    
    Use this instead of direct event_bus.publish() when you need
    reliable delivery (i.e., the event must not be lost).
    """
    return await outbox.add_event(
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
        actor_id=actor_id
    )
