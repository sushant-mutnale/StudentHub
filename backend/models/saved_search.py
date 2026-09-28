"""
Saved Searches Model

Stores recruiter saved candidate searches for reuse and alert triggers.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from bson import ObjectId

from ..database import get_database


def saved_searches_collection():
    return get_database()["saved_searches"]


async def create_saved_search(recruiter_id: str, data: dict) -> dict:
    now = datetime.utcnow()
    doc = {
        "recruiter_id": ObjectId(recruiter_id),
        "name": data.get("name") or data.get("title") or "Untitled search",
        "filters": {
            "skill": data.get("skill"),
            "location": data.get("location"),
            "college": data.get("college"),
            "min_score": data.get("min_score"),
        },
        "alert_enabled": data.get("alert_enabled", True),
        "last_checked_at": None,
        "last_match_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await saved_searches_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_saved_searches(recruiter_id: str) -> List[dict]:
    cursor = (
        saved_searches_collection()
        .find({"recruiter_id": ObjectId(recruiter_id)})
        .sort("created_at", -1)
    )
    return await cursor.to_list(length=100)


async def get_saved_search(search_id: str, recruiter_id: str) -> Optional[dict]:
    return await saved_searches_collection().find_one(
        {"_id": ObjectId(search_id), "recruiter_id": ObjectId(recruiter_id)}
    )


async def delete_saved_search(search_id: str, recruiter_id: str) -> bool:
    result = await saved_searches_collection().delete_one(
        {"_id": ObjectId(search_id), "recruiter_id": ObjectId(recruiter_id)}
    )
    return result.deleted_count > 0


async def update_saved_search(search_id: str, recruiter_id: str, data: dict) -> Optional[dict]:
    update_data = {"updated_at": datetime.utcnow()}
    if "alert_enabled" in data:
        update_data["alert_enabled"] = data["alert_enabled"]
    if "name" in data:
        update_data["name"] = data["name"]
    if "filters" in data:
        update_data["filters"] = data["filters"]

    result = await saved_searches_collection().find_one_and_update(
        {"_id": ObjectId(search_id), "recruiter_id": ObjectId(recruiter_id)},
        {"$set": update_data},
        return_document=True,
    )
    return result


async def get_candidates_for_search(search_id: str, recruiter_id: str, limit: int = 20) -> List[dict]:
    search = await get_saved_search(search_id, recruiter_id)
    if not search:
        return []
    from ..models.user import users_collection
    filters = search.get("filters", {})
    query: Dict[str, Any] = {"role": "student"}
    if filters.get("skill"):
        query["skills"] = {"$regex": filters["skill"], "$options": "i"}
    if filters.get("location"):
        query["location"] = {"$regex": filters["location"], "$options": "i"}
    if filters.get("college"):
        query["college"] = {"$regex": filters["college"], "$options": "i"}

    cursor = users_collection().find(query).limit(limit)
    students = await cursor.to_list(length=limit)
    return students


async def run_saved_search_alerts():
    """Background job: for each saved search with alerts enabled, run the query
    and create a notification if new students match since last check."""
    from ..models.user import users_collection
    from ..models.notification import create_notification
    from datetime import timedelta

    results = {"searches_checked": 0, "alerts_sent": 0}
    now = datetime.utcnow()

    cursor = saved_searches_collection().find({"alert_enabled": True})
    searches = await cursor.to_list(length=200)

    for search in searches:
        recruiter_id = str(search["recruiter_id"])
        search_id = str(search["_id"])
        filters = search.get("filters", {})

        query: Dict[str, Any] = {"role": "student"}

        if filters.get("skill"):
            query["skills"] = {"$regex": filters["skill"], "$options": "i"}
        if filters.get("location"):
            query["location"] = {"$regex": filters["location"], "$options": "i"}
        if filters.get("college"):
            query["college"] = {"$regex": filters["college"], "$options": "i"}

        last_checked = search.get("last_checked_at")
        if last_checked:
            query["created_at"] = {"$gt": last_checked}

        students_cursor = users_collection().find(query).limit(50)
        new_students = await students_cursor.to_list(length=50)
        match_count = len(new_students)

        results["searches_checked"] += 1

        # Update search metadata
        await saved_searches_collection().update_one(
            {"_id": search["_id"]},
            {
                "$set": {
                    "last_checked_at": now,
                    "last_match_count": match_count,
                }
            },
        )

        if match_count > 0:
            try:
                from ..models.notification import create_notification
                search_name = search.get("name") or "Your saved search"
                skill_hint = f" for {filters['skill']}" if filters.get("skill") else ""
                await create_notification(
                    recruiter_id,
                    "candidate_alert",
                    {
                        "saved_search_id": search_id,
                        "search_name": search_name,
                        "new_match_count": match_count,
                        "message": f"{match_count} student(s) added since your last check.",
                        "skill_filter": filters.get("skill"),
                        "location_filter": filters.get("location"),
                    },
                    priority="medium",
                    category="alert",
                )
                results["alerts_sent"] += 1
            except Exception:
                pass

    return results
