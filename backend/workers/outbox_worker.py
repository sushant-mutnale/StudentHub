"""
Outbox Worker

Polls the outbox table and publishes pending events to the event bus.
This ensures reliable event delivery even if the event bus was
temporarily unavailable when the event was created.

Features:
- Polls for pending events
- Publishes to event bus
- Handles retries for failed events
- Cleans up old processed events
"""

import logging
from typing import List

from .worker_base import BackgroundWorker
from ..models.outbox import outbox, OutboxEvent
from ..events import event_bus, EventTypes

logger = logging.getLogger(__name__)


class OutboxWorker(BackgroundWorker):
    """
    Worker that processes the transactional outbox.
    
    Polls the outbox collection for pending events and publishes
    them to the event bus.
    """
    
    def __init__(self, poll_interval: float = 2.0, batch_size: int = 50):
        super().__init__(
            name="outbox_worker",
            poll_interval=poll_interval,
            batch_size=batch_size
        )
    
    async def get_jobs(self) -> List[OutboxEvent]:
        """Get pending outbox events."""
        return await outbox.get_pending_events(limit=self.batch_size)
    
    async def process_job(self, event: OutboxEvent) -> bool:
        """
        Process an outbox event by publishing it to the event bus.
        """
        try:
            # Mark as processing
            await outbox.mark_processing(event.id)
            
            # Convert string event type to enum (if valid)
            try:
                event_type = EventTypes(event.event_type)
            except ValueError:
                # Unknown event type, log and skip
                logger.warning(f"Unknown event type: {event.event_type}")
                await outbox.mark_processed(event.id)
                return True
            
            # Publish to event bus
            await event_bus.publish(
                event_type=event_type,
                payload=event.payload,
                correlation_id=event.correlation_id,
                actor_id=event.actor_id
            )
            
            # Mark as processed
            await outbox.mark_processed(event.id)
            
            logger.debug(
                f"Published outbox event: {event.event_type}",
                extra={"event_id": event.id}
            )
            
            return True
            
        except Exception as e:
            await outbox.mark_failed(event.id, str(e))
            raise
    
    async def on_job_failure(self, event: OutboxEvent, error: Exception):
        """Log failure details."""
        logger.error(
            f"Failed to publish outbox event: {event.event_type}",
            extra={
                "event_id": event.id,
                "attempts": event.attempts,
                "error": str(error)
            }
        )


class OutboxCleanupWorker(BackgroundWorker):
    """
    Worker that cleans up old processed outbox events.
    
    Runs periodically (e.g., hourly) to remove events that have
    been successfully processed and are older than the retention period.
    """
    
    def __init__(
        self,
        poll_interval: float = 3600.0,  # 1 hour
        retention_days: int = 7
    ):
        super().__init__(
            name="outbox_cleanup_worker",
            poll_interval=poll_interval
        )
        self.retention_days = retention_days
    
    async def get_jobs(self) -> list:
        """Return a single 'cleanup' job each poll interval."""
        return [{"action": "cleanup"}]
    
    async def process_job(self, job) -> bool:
        """Run the cleanup."""
        await outbox.cleanup_old_events(days=self.retention_days)
        return True
