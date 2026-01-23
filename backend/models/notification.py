from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from ..database import get_database


def notifications_collection():
    return get_database()["notifications"]


async def create_notification(user_id: str, kind: str, payload: Dict[str, Any]):
    if not ObjectId.is_valid(user_id):
        return
    doc = {
        "user_id": ObjectId(user_id),
        "kind": kind,
        "payload": payload,
        "is_read": False,
        "created_at": datetime.utcnow(),
    }
    await notifications_collection().insert_one(doc)


