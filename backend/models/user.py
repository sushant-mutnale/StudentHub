from datetime import datetime

from bson import ObjectId

from ..database import get_database


def users_collection():
    return get_database()["users"]


def migrate_user_skills(user_doc: dict) -> dict:
    """Helper to migrate old string-based skills to structured objects and init AI profile."""
    if not user_doc:
        return user_doc
    
    modified = False
    skills = user_doc.get("skills", [])
    if skills and isinstance(skills[0], str):
        user_doc["skills"] = [
            {
                "name": s.lower().strip(),
                "level": 50,
                "proficiency": "Intermediate",
                "confidence": 30,
                "evidence": [],
                "last_updated": datetime.utcnow()
            }
            for s in skills
        ]
        modified = True
    
    if user_doc.get("role") == "student" and "ai_profile" not in user_doc:
        user_doc["ai_profile"] = {
            "overall_score": 0.0,
            "skill_score": 0.0,
            "learning_score": 0.0,
            "interview_score": 0.0,
            "activity_score": 0.0,
            "profile_completeness": 0.0,
            "last_computed_at": datetime.utcnow()
        }
        modified = True
    
    if modified:
        # We don't necessarily need to save it back here, but it's good for consistency
        # In a real app we might want to schedule a background update
        pass
        
    return user_doc


async def create_user(user_data: dict):
    now = datetime.utcnow()
    user_data["created_at"] = now
    user_data["updated_at"] = now
    
    # Initialize AI profile for new students
    if user_data.get("role") == "student" and "ai_profile" not in user_data:
        user_data["ai_profile"] = {
            "overall_score": 0.0,
            "skill_score": 0.0,
            "learning_score": 0.0,
            "interview_score": 0.0,
            "activity_score": 0.0,
            "profile_completeness": 0.0,
            "last_computed_at": now
        }
        
    result = await users_collection().insert_one(user_data)
    user = await users_collection().find_one({"_id": result.inserted_id})
    return migrate_user_skills(user)


async def get_user_by_username(username: str):
    user = await users_collection().find_one({"username": username})
    return migrate_user_skills(user)


async def get_user_by_email(email: str):
    user = await users_collection().find_one({"email": email})
    return migrate_user_skills(user)


async def get_user_by_id(user_id: str):
    user = await users_collection().find_one({"_id": ObjectId(user_id)})
    return migrate_user_skills(user)


async def get_users_by_ids(user_ids: list[str]):
    valid_ids = [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]
    if not valid_ids:
        return []
    cursor = users_collection().find({"_id": {"$in": valid_ids}})
    users = await cursor.to_list(length=None)
    return [migrate_user_skills(u) for u in users]


async def get_users_by_usernames(usernames: list[str]):
    if not usernames:
        return []
    cursor = users_collection().find({"username": {"$in": usernames}})
    users = await cursor.to_list(length=None)
    return [migrate_user_skills(u) for u in users]


async def update_user(user_id: str, updates: dict):
    updates["updated_at"] = datetime.utcnow()
    # If skills are being updated, ensure they are in the new format if strings are passed
    if "skills" in updates and updates["skills"] and isinstance(updates["skills"][0], str):
        updates["skills"] = [
            {
                "name": s.lower().strip(),
                "level": 50,
                "proficiency": "Intermediate",
                "confidence": 30,
                "evidence": [],
                "last_updated": datetime.utcnow()
            }
            for s in updates["skills"]
        ]
        
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return await get_user_by_id(user_id)


async def list_students_by_skill_matches(skills: list[str]):
    # Normalize input skills for searching
    normalized_skills = [s.lower().strip() for s in skills]
    cursor = users_collection().find({
        "role": "student", 
        "skills.name": {"$in": normalized_skills}
    })
    students = await cursor.to_list(length=None)
    return [migrate_user_skills(s) for s in students]


async def update_user_password(user_id: str, new_password_hash: str):
    """Update user's password hash."""
    await users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "password_hash": new_password_hash,
            "updated_at": datetime.utcnow()
        }}
    )
