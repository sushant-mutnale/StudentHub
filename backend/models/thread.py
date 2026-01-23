from datetime import datetime

from bson import ObjectId

from ..database import get_database


def threads_collection():
    return get_database()["threads"]


def messages_collection():
    return get_database()["messages"]


def build_participant_hash(participant_ids: list[str]) -> str:
    """Deterministic hash for participant sets (sorted string IDs)."""
    return "|".join(sorted(participant_ids))


async def ensure_message_indexes():
    threads = threads_collection()
    messages = messages_collection()

    await threads.create_index("participants")
    await threads.create_index("participant_hash", unique=True)
    await threads.create_index([("last_message_at", -1)])

    await messages.create_index([("thread_id", 1), ("created_at", 1)])
    await messages.create_index("sender_id")


def serialize_object_id(document: dict, field: str):
    if field in document and isinstance(document[field], ObjectId):
        document[field] = str(document[field])
    return document


async def get_thread_by_id(thread_id: str) -> dict | None:
    if not ObjectId.is_valid(thread_id):
        return None
    return await threads_collection().find_one({"_id": ObjectId(thread_id)})


async def append_text_message(thread_id: str, sender_id: str, text: str) -> dict | None:
    """Append a plain text message to a thread and update unread counts."""
    thread = await get_thread_by_id(thread_id)
    if not thread or not ObjectId.is_valid(sender_id):
        return None

    sender_obj = ObjectId(sender_id)
    now = datetime.utcnow()
    message_doc = {
        "thread_id": thread["_id"],
        "sender_id": sender_obj,
        "text": text,
        "created_at": now,
        "read_by": [sender_obj],
    }
    insert_result = await messages_collection().insert_one(message_doc)
    message_doc["_id"] = insert_result.inserted_id

    unread_counts = thread.get("unread_counts", {})
    for participant in thread.get("participants", []):
        pid = str(participant)
        if pid == sender_id:
            unread_counts[pid] = 0
        else:
            unread_counts[pid] = unread_counts.get(pid, 0) + 1

    await threads_collection().update_one(
        {"_id": thread["_id"]},
        {
            "$set": {
                "last_message_at": now,
                "last_message_preview": text[:140],
                "unread_counts": unread_counts,
                "updated_at": now,
            }
        },
    )
    return message_doc

