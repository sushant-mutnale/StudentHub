from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from ..database import get_database

def connections_collection():
    return get_database()["connection_requests"]

async def create_connection_request(sender_id: str, receiver_id: str):
    now = datetime.utcnow()
    doc = {
        "sender_id": ObjectId(sender_id),
        "receiver_id": ObjectId(receiver_id),
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }
    result = await connections_collection().insert_one(doc)
    return result.inserted_id

async def get_request_by_id(request_id: str):
    if not ObjectId.is_valid(request_id):
        return None
    return await connections_collection().find_one({"_id": ObjectId(request_id)})

async def find_existing_request(user_a: str, user_b: str):
    """Find a pending or accepted request between two users."""
    id_a = ObjectId(user_a)
    id_b = ObjectId(user_b)
    return await connections_collection().find_one({
        "$or": [
            {"sender_id": id_a, "receiver_id": id_b},
            {"sender_id": id_b, "receiver_id": id_a}
        ]
    })

async def update_request_status(request_id: str, status: str):
    await connections_collection().update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )

async def get_pending_requests(user_id: str):
    cursor = connections_collection().find({
        "receiver_id": ObjectId(user_id),
        "status": "pending"
    })
    return await cursor.to_list(length=None)
