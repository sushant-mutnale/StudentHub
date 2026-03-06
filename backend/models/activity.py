from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from ..database import get_database


def activities_collection():
    return get_database()["activities"]


async def log_activity(
    user_id: str, 
    event_type: str, 
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log a system activity.
    Types: POST_CREATED, JOB_APPLIED, INTERVIEW_ACCEPTED, MESSAGE_SENT, etc.
    """
    if not ObjectId.is_valid(user_id):
        return None
        
    doc = {
        "user_id": ObjectId(user_id),
        "event_type": event_type,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow()
    }
    result = await activities_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_user_activities(user_id: str, limit: int = 50):
    if not ObjectId.is_valid(user_id):
        return []
        
    cursor = activities_collection().find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=None)
