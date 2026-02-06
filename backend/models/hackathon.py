from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_database

def hackathons_collection():
    return get_database()["hackathons"]

async def list_hackathons(limit=20, skip=0) -> List[dict]:
    """List hackathons with pagination."""
    cursor = hackathons_collection().find().sort("start_date", 1).skip(skip).limit(limit)
    return await cursor.to_list(length=None)

async def create_hackathon(data: dict) -> dict:
    """Create a new hackathon."""
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()
    result = await hackathons_collection().insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def seed_default_hackathons():
    """Seed some default hackathons if none exist."""
    count = await hackathons_collection().count_documents({})
    if count == 0:
        defaults = [
            {
                "title": "AI Innovation Hacks",
                "description": "Build the next generation of AI tools.",
                "organizer": "TechGiant Corp",
                "start_date": datetime.utcnow(),
                "end_date": datetime.utcnow(),
                "registration_deadline": datetime.utcnow(),
                "location": "Online",
                "is_virtual": True,
                "prizes": ["$10,000", "Internship"],
                "skills": ["Python", "TensorFlow", "NLP"],
                "participants_count": 150,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Web3 Future Builder",
                "description": "Decentralized apps for the future.",
                "organizer": "BlockFoundation",
                "start_date": datetime.utcnow(),
                "end_date": datetime.utcnow(),
                "registration_deadline": datetime.utcnow(),
                "location": "San Francisco, CA",
                "is_virtual": False,
                "prizes": ["$5,000", "Tokens"],
                "skills": ["Solidity", "React", "Rust"],
                "participants_count": 80,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        await hackathons_collection().insert_many(defaults)
        print("Seeded default hackathons.")
