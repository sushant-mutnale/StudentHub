from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from ..database import get_database


def jobs_collection():
    return get_database()["jobs"]


def job_applications_collection():
    return get_database()["job_applications"]


async def create_job(recruiter: dict, data: dict):
    """Insert a new job for the given recruiter.

    The recruiter_id is always taken from the authenticated recruiter document
    to prevent spoofing. Visibility defaults to "public" if omitted.
    """
    now = datetime.utcnow()
    visibility = data.get("visibility") or "public"

    job = {
        "recruiter_id": ObjectId(recruiter["_id"]),
        "company_name": recruiter.get("company_name"),
        "title": data["title"],
        "description": data["description"],
        "skills_required": data["skills_required"],
        "location": data["location"],
        "visibility": visibility,
        "created_at": now,
        "updated_at": now,
    }
    result = await jobs_collection().insert_one(job)
    return await jobs_collection().find_one({"_id": result.inserted_id})


async def list_jobs_by_recruiter(recruiter_id: str):
    cursor = jobs_collection().find({"recruiter_id": ObjectId(recruiter_id)}).sort(
        "created_at", -1
    )
    return await cursor.to_list(length=None)


async def list_jobs_for_user(
    user: dict,
    *,
    q: Optional[str] = None,
    skills: Optional[List[str]] = None,
    location: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
):
    """Return jobs visible to the given user with optional filters applied.

    - Students see only public/student-visible jobs.
    - Recruiters see their own jobs plus public/student-visible jobs.
    - Other roles (if any) fall back to public/student-visible jobs.
    """
    role = user.get("role")

    # Base visibility predicate for jobs visible to all students.
    public_visibility_filter: Dict[str, Any] = {
        "$or": [
            {"visibility": {"$in": ["public", "students"]}},
            # Backward compatibility: treat jobs without visibility as public.
            {"visibility": {"$exists": False}},
        ]
    }

    base_filter: Dict[str, Any]
    if role == "recruiter":
        base_filter = {
            "$or": [
                {"recruiter_id": ObjectId(user["_id"])},
                public_visibility_filter,
            ]
        }
    else:
        # Students and any other roles only see public/student-visible jobs.
        base_filter = public_visibility_filter

    conditions: List[Dict[str, Any]] = [base_filter]

    if q:
        # Simple, index-friendly regex search over title/description.
        text_query = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]
        }
        conditions.append(text_query)

    if skills:
        skills_clean = [s.strip() for s in skills if s.strip()]
        if skills_clean:
            # Require that all requested skills are present.
            conditions.append({"skills_required": {"$all": skills_clean}})

    if location:
        conditions.append({"location": {"$regex": location, "$options": "i"}})

    if len(conditions) == 1:
        mongo_query: Dict[str, Any] = conditions[0]
    else:
        mongo_query = {"$and": conditions}

    # Basic safety bounds for pagination.
    safe_limit = max(1, min(int(limit), 100))
    safe_skip = max(0, int(skip))

    cursor = (
        jobs_collection()
        .find(mongo_query)
        .sort("created_at", -1)
        .skip(safe_skip)
        .limit(safe_limit)
    )
    return await cursor.to_list(length=safe_limit)


async def get_job(job_id: str):
    return await jobs_collection().find_one({"_id": ObjectId(job_id)})


async def delete_job(job_id: str, recruiter_id: str):
    await jobs_collection().delete_one(
        {"_id": ObjectId(job_id), "recruiter_id": ObjectId(recruiter_id)}
    )


async def create_job_application(job_id: str, student: dict, data: dict):
    """Create a job application for the given job by the given student."""
    job = await get_job(job_id)
    if not job:
        return None

    now = datetime.utcnow()
    application = {
        "job_id": ObjectId(job_id),
        "student_id": ObjectId(student["_id"]),
        "student_name": student.get("full_name"),
        "student_username": student.get("username"),
        "message": data.get("message", ""),
        "resume_url": data.get("resume_url"),
        "created_at": now,
    }
    result = await job_applications_collection().insert_one(application)
    return await job_applications_collection().find_one({"_id": result.inserted_id})


async def list_applications_for_job(job_id: str, recruiter: dict):
    """List applications for a job, only if the recruiter owns that job."""
    job = await get_job(job_id)
    if not job or str(job.get("recruiter_id")) != str(recruiter["_id"]):
        return None

    cursor = (
        job_applications_collection()
        .find({"job_id": ObjectId(job_id)})
        .sort("created_at", -1)
    )
    return await cursor.to_list(length=None)


async def ensure_job_indexes():
    """Create indexes to keep job queries and applications fast."""
    col = jobs_collection()
    # Index by recruiter for /jobs/my and recruiter visibility.
    await col.create_index("recruiter_id")
    # Multikey index for skills_required.
    await col.create_index("skills_required")
    # Text index for title/description to support q searches.
    await col.create_index([("title", "text"), ("description", "text")])
    # Sort index for recency.
    await col.create_index("created_at")

    # Job applications indexes
    app_col = job_applications_collection()
    await app_col.create_index("job_id")
    await app_col.create_index("student_id")
    await app_col.create_index("created_at")

