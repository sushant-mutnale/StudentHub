"""
Worker Runner

Entry point to start all background workers.
"""

import asyncio
import logging
import signal
import sys
import os

# Ensure backend module is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import connect_to_mongo, close_mongo_connection
from backend.workers.worker_base import worker_manager
from backend.workers.outbox_worker import OutboxWorker, OutboxCleanupWorker
from backend.workers.recommendation_worker import RecommendationWorker
from backend.workers.notification_worker import NotificationWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main worker entry point."""
    logger.info("Starting Worker Service...")
    
    # 1. Connect to Resources
    await connect_to_mongo()
    
    # 2. Register Workers
    # Outbox: Essential for event reliability
    worker_manager.register(OutboxWorker(poll_interval=2.0))
    worker_manager.register(OutboxCleanupWorker(poll_interval=3600))
    
    # Notifications: Deliver pending alerts
    worker_manager.register(NotificationWorker(poll_interval=5.0))
    
    # Recommendations: Periodically update
    # In prod, this might run less frequently (e.g. 1 hour)
    worker_manager.register(RecommendationWorker(poll_interval=60.0)) 
    
    # 3. Start All
    await worker_manager.start_all()
    
    # 4. Keep Alive / Handle Shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def handle_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    # Register signal handlers for graceful shutdown (non-Windows mostly, but try)
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGTERM, handle_signal)
        loop.add_signal_handler(signal.SIGINT, handle_signal)
    else:
        # Windows simple handling via KeyboardInterrupt if running in console
        # Loop signal handlers are not supported on Windows ProactorLoop usually
        pass

    try:
        # Wait until asked to stop
        while not stop_event.is_set():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    finally:
        logger.info("Shutting down workers...")
        await worker_manager.stop_all()
        await close_mongo_connection()
        logger.info("Worker Service Stopped")

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Windows specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
