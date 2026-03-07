import logging
import asyncio
from typing import Optional

from .worker_base import BackgroundWorker
from ..services.opportunity_ingestion import opportunity_ingestion
from ..config import settings

logger = logging.getLogger(__name__)

class IngestionWorker(BackgroundWorker):
    """
    Worker that periodically ingests opportunities (Jobs, Hackathons, Content).
    Runs every 12 hours by default.
    """
    
    def __init__(self, poll_interval: float = 43200): # 12 hours
        super().__init__(name="ingestion_worker", poll_interval=poll_interval)
    
    async def _polling_loop(self) -> None:
        """
        Internal polling loop that triggers ingestion.
        """
        logger.info(f"IngestionWorker: Started polling loop (interval: {self.poll_interval}s)")
        
        while self.running:
            try:
                logger.info("IngestionWorker: Starting scheduled ingestion...")
                # We pass use_mock=False to attempt real scraping
                result = await opportunity_ingestion.ingest_all(use_mock=False)
                logger.info(f"IngestionWorker: Ingestion completed. Stats: {result}")
            except Exception as e:
                logger.error(f"IngestionWorker cycle failed: {e}")
            
            await asyncio.sleep(self.poll_interval)
