from datetime import datetime

from bson import ObjectId

from ..database import get_database


def messages_collection():
    return get_database()["messages"]


async def send_message(sender_id: str, receiver_id: str, content: str):
    message = {
        "sender_id": ObjectId(sender_id),
        "receiver_id": ObjectId(receiver_id),
        "content": content,
        "created_at": datetime.utcnow(),
        "read": False,
    }
    result = await messages_collection().insert_one(message)
    return await messages_collection().find_one({"_id": result.inserted_id})


async def conversation(user_id: str, other_id: str):
    cursor = messages_collection().find(
        {
            "$or": [
                {
                    "sender_id": ObjectId(user_id),
                    "receiver_id": ObjectId(other_id),
                },
                {
                    "sender_id": ObjectId(other_id),
                    "receiver_id": ObjectId(user_id),
                },
            ]
        }
    ).sort("created_at", 1)
    return await cursor.to_list(length=None)



