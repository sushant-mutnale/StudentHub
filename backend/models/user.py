from datetime import datetime

from bson import ObjectId

from ..database import get_database


def users_collection():
    return get_database()["users"]


async def create_user(user_data: dict):
    now = datetime.utcnow()
    user_data["created_at"] = now
    user_data["updated_at"] = now
    result = await users_collection().insert_one(user_data)
    return await users_collection().find_one({"_id": result.inserted_id})


async def get_user_by_username(username: str):
    return await users_collection().find_one({"username": username})


async def get_user_by_email(email: str):
    return await users_collection().find_one({"email": email})


async def get_user_by_id(user_id: str):
    return await users_collection().find_one({"_id": ObjectId(user_id)})


async def get_users_by_ids(user_ids: list[str]):
    valid_ids = [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]
    if not valid_ids:
        return []
    cursor = users_collection().find({"_id": {"$in": valid_ids}})
    return await cursor.to_list(length=None)


async def get_users_by_usernames(usernames: list[str]):
    if not usernames:
        return []
    cursor = users_collection().find({"username": {"$in": usernames}})
    return await cursor.to_list(length=None)


async def update_user(user_id: str, updates: dict):
    updates["updated_at"] = datetime.utcnow()
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return await get_user_by_id(user_id)


async def list_students_by_skill_matches(skills: list[str]):
    return (
        await users_collection()
        .find({"role": "student", "skills": {"$in": skills}})
        .to_list(length=None)
    )


