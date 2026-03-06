from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from ..database import get_database


def notifications_collection():
    return get_database()["notifications"]


async def create_notification(
    user_id: str, 
    kind: str, 
    payload: Dict[str, Any],
    priority: str = "medium",  # low, medium, high
    category: str = "general"   # alert, message, interview, offer
):
    if not ObjectId.is_valid(user_id):
        return
    doc = {
        "user_id": ObjectId(user_id),
        "kind": kind,
        "payload": payload,
        "is_read": False,
        "read_at": None,
        "priority": priority,
        "category": category,
        "delivery_status": "pending", # pending, sent, failed
        "delivery_attempts": 0,
        "created_at": datetime.utcnow(),
    }
    await notifications_collection().insert_one(doc)


async def mark_notification_as_read(notification_id: str):
    if not ObjectId.is_valid(notification_id):
        return
    await notifications_collection().update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )


