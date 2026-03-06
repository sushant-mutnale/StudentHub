
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from backend.database import connect_to_mongo, get_database
from datetime import datetime

async def seed():
    print("Seeding DB...")
    await connect_to_mongo()
    db = get_database()
    
    job = {
        "title": "Senior Python Developer",
        "recruiter_id": "test_recruiter",
        "description": "We need a Python expert with FastAPI, AWS, and specific knowledge of React for frontend. Docker experience is mandatory.",
        "company_name": "Tech Corp",
        "location": "Remote",
        "created_at": datetime.utcnow(),
        "visibility": "public"
    }
    
    res = await db["jobs"].insert_one(job)
    print(f"Inserted Job: {res.inserted_id}")

if __name__ == "__main__":
    asyncio.run(seed())
