from datetime import datetime

from bson import ObjectId

from ..database import get_database


def posts_collection():
    return get_database()["posts"]


async def create_post(author: dict, data: dict):
    now = datetime.utcnow()
    post = {
        "author_id": ObjectId(author["_id"]),
        "author_name": author.get("full_name") or author.get("company_name"),
        "author_username": author["username"],
        "author_role": author["role"],
        "author_avatar_url": author.get("avatar_url"),
        "content": data["content"],
        "tags": data.get("tags", []),
        "created_at": now,
        "updated_at": now,
        "likes": [],
        "comments": [],
    }
    result = await posts_collection().insert_one(post)
    return await posts_collection().find_one({"_id": result.inserted_id})


async def list_posts():
    cursor = posts_collection().find().sort("created_at", -1)
    return await cursor.to_list(length=None)


async def list_posts_by_user(user_id: str):
    cursor = posts_collection().find({"author_id": ObjectId(user_id)}).sort(
        "created_at", -1
    )
    return await cursor.to_list(length=None)


async def get_post(post_id: str):
    return await posts_collection().find_one({"_id": ObjectId(post_id)})


async def update_post(post_id: str, updates: dict):
    updates["updated_at"] = datetime.utcnow()
    await posts_collection().update_one({"_id": ObjectId(post_id)}, {"$set": updates})
    return await get_post(post_id)


async def delete_post(post_id: str):
    await posts_collection().delete_one({"_id": ObjectId(post_id)})


async def toggle_like(post_id: str, user_id: str):
    post = await get_post(post_id)
    if not post:
        return None

    likes = post.get("likes", [])
    user_obj_id = ObjectId(user_id)
    if user_obj_id in likes:
        await posts_collection().update_one(
            {"_id": ObjectId(post_id)},
            {"$pull": {"likes": user_obj_id}},
        )
    else:
        await posts_collection().update_one(
            {"_id": ObjectId(post_id)},
            {"$addToSet": {"likes": user_obj_id}},
        )
    return await get_post(post_id)


async def add_comment(post_id: str, user_id: str, text: str):
    comment = {
        "_id": ObjectId(),
        "user_id": ObjectId(user_id),
        "text": text,
        "created_at": datetime.utcnow(),
    }
    await posts_collection().update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"comments": comment}},
    )
    return await get_post(post_id)

