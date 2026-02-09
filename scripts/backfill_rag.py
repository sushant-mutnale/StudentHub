
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_database, connect_to_mongo
from backend.events.event_bus import event_bus, Events
from backend.workers.rag_worker import rag_worker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_jobs():
    print("Starting RAG Backfill for Jobs...")
    
    # 0. Connect to DB
    await connect_to_mongo()
    
    # 1. Start RAG Worker to consume events
    await rag_worker.start()
    
    # 2. Fetch all jobs from DB
    db = get_database()
    jobs_cursor = db["jobs"].find({})
    jobs = await jobs_cursor.to_list(length=10000)
    
    print(f"Found {len(jobs)} jobs in database.")
    
    # 3. Publish events
    count = 0
    for job in jobs:
        # Construct payload matching JOB_POSTED schema
        payload = {
            "id": str(job["_id"]),
            "title": job.get("title", ""),
            "description": job.get("description", ""),
            "company_name": job.get("company_name", ""),
            "location": job.get("location", "")
        }
        
        await event_bus.publish(Events.JOB_POSTED, payload)
        count += 1
        if count % 10 == 0:
            print(f"Queued {count} jobs...")
            
    # 4. Wait for processing
    print("Waiting for worker to finish processing...")
    # Since event bus is fire-and-forget, we just wait a set time or until queue empty
    # For a script, a fixed sleep is acceptable if queue size is small
    await asyncio.sleep(10) 
    
    await rag_worker.stop()
    print(f"Backfill complete! Queued {count} jobs for vectorization.")

if __name__ == "__main__":
    # Ensure event loop handles async correctly
    asyncio.run(backfill_jobs())
