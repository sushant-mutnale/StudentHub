"""
Base Worker Class

Provides common functionality for background workers.
"""

import asyncio
import logging
from ..events.event_bus import event_bus

logger = logging.getLogger(__name__)

class BackgroundWorker:
    """
    Base class for background workers.
    Subclasses should implement `handle_event`.
    """
    
    def __init__(self, name: str, subscribed_events: list = None, poll_interval: float = None, batch_size: int = 10):
        self.name = name
        self.subscribed_events = subscribed_events or []
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.running = False
        self._poll_task = None
        
    async def start(self):
        """Start the worker (subscriptions + polling)."""
        logger.info(f"Starting worker: {self.name}")
        self.running = True
        
        # 1. Register Subscriptions
        for event_type in self.subscribed_events:
            event_bus.subscribe(event_type, self.handle_event)
            
        # 2. Start Polling Loop if configured
        if self.poll_interval:
            self._poll_task = asyncio.create_task(self._polling_loop())

    async def stop(self):
        self.running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Worker {self.name} stopped")

    async def _polling_loop(self):
        """Internal polling loop."""
        logger.info(f"Started polling loop for {self.name}")
        while self.running:
            try:
                jobs = await self.get_jobs()
                if jobs:
                    for job in jobs:
                        await self.process_job(job)
                else:
                    # Sleep only if no jobs found to avoid busy loop? 
                    # Actually usually we sleep anyway or depending on logic.
                    # For simple polling, we sleep after each check.
                    pass
            except Exception as e:
                logger.error(f"Error in parsing loop for {self.name}: {e}")
            
            await asyncio.sleep(self.poll_interval)

    async def get_jobs(self) -> list:
        """Override to fetch jobs for polling."""
        return []

    async def process_job(self, job) -> bool:
        """Override to process a polled job."""
        return True

    async def handle_event(self, event: dict):
        """
        Process an event. Must be implemented by subclasses if they subscribe to events.
        """
        pass

class WorkerManager:
    """
    Manages the lifecycle of multiple background workers.
    """
    def __init__(self):
        self.workers = []

    def register(self, worker: BackgroundWorker):
        self.workers.append(worker)

    async def start_all(self):
        logger.info("Starting all background workers...")
        for worker in self.workers:
            await worker.start()

    async def stop_all(self):
        logger.info("Stopping all background workers...")
        for worker in self.workers:
            await worker.stop()

# Singleton instance
worker_manager = WorkerManager()
