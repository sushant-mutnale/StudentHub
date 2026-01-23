from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from ..database import get_database


def interviews_collection():
    return get_database()["interviews"]


async def ensure_interview_indexes():
    collection = interviews_collection()
    await collection.create_index("candidate_id")
    await collection.create_index("recruiter_id")
    await collection.create_index("job_id")
    await collection.create_index([("scheduled_slot.start", 1)])


def default_history_entry(action: str, actor_id: str, meta: Dict[str, Any] | None = None):
    return {
        "action": action,
        "by": ObjectId(actor_id),
        "at": datetime.utcnow(),
        "meta": meta or {},
    }


