
import asyncio
import sys
import os

# Add project root to path (3 levels up from this file)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.opportunity_ingestion import opportunity_ingestion
from backend.database import connect_to_mongo, close_mongo_connection

async def main():
    print("Connecting to database...")
    await connect_to_mongo()
    
    print("Starting immediate ingestion (REAL DATA)...")
    try:
        # User requested to "scrap the job" -> specifically jobs
        # But ingest_all does everything. Let's do ingest_all with use_mock=False
        result = await opportunity_ingestion.ingest_all(use_mock=False)
        print("Ingestion completed successfully!")
        print(result)
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
