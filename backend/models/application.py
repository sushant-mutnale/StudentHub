"""
Application Models - Unified application tracking per (job_id, student_id).

This is the core ATS object that links:
- Pipeline stage tracking
- Message threads
- Interview records
- Offer records
- Notes, tags, and evaluations
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from ..database import get_database


def applications_collection():
    return get_database()["applications"]


# Application statuses
STATUS_ACTIVE = "active"
STATUS_WITHDRAWN = "withdrawn"
STATUS_HIRED = "hired"
STATUS_REJECTED = "rejected"
STATUS_ARCHIVED = "archived"


async def create_application(
    job_id: str,
    student_id: str,
    company_id: str,
    pipeline_template_id: str,
    pipeline_version: int,
    initial_stage_id: str,
    initial_stage_name: str,
    thread_id: Optional[str] = None
) -> dict:
    """Create a new application record when student applies to job."""
    now = datetime.utcnow()
    
    application = {
        "job_id": ObjectId(job_id),
        "student_id": ObjectId(student_id),
        "company_id": ObjectId(company_id),
        "pipeline_template_id": ObjectId(pipeline_template_id),
        "pipeline_version": pipeline_version,
        "current_stage_id": initial_stage_id,
        "current_stage_name": initial_stage_name,
        "stage_history": [
            {
                "stage_id": initial_stage_id,
                "stage_name": initial_stage_name,
                "changed_by": str(student_id),
                "timestamp": now,
                "reason": "Initial application"
            }
        ],
        "thread_id": ObjectId(thread_id) if thread_id else None,
        "interview_ids": [],
        "offer_id": None,
        "notes": [],
        "tags": [],
        "rating_summary": {
            "overall_score": None,
            "scorecard_count": 0,
            "last_updated": None
        },
        "student_visible_stage": "Application Received",
        "status": STATUS_ACTIVE,
        "applied_at": now,
        "created_at": now,
        "updated_at": now
    }
    
    result = await applications_collection().insert_one(application)
    return await applications_collection().find_one({"_id": result.inserted_id})


async def get_application(application_id: str) -> Optional[dict]:
    """Get an application by ID."""
    return await applications_collection().find_one({"_id": ObjectId(application_id)})


async def get_application_by_job_student(job_id: str, student_id: str) -> Optional[dict]:
    """Get the application for a specific job and student."""
    return await applications_collection().find_one({
        "job_id": ObjectId(job_id),
        "student_id": ObjectId(student_id)
    })


async def list_applications_for_job(
    job_id: str,
    stage_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> List[dict]:
    """List all applications for a job, optionally filtered by stage or status."""
    query: Dict[str, Any] = {"job_id": ObjectId(job_id)}
    
    if stage_id:
        query["current_stage_id"] = stage_id
    if status:
        query["status"] = status
    
    cursor = applications_collection().find(query).sort("applied_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


async def list_applications_for_student(
    student_id: str,
    status: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """List all applications for a student."""
    query: Dict[str, Any] = {"student_id": ObjectId(student_id)}
    if status:
        query["status"] = status
    
    cursor = applications_collection().find(query).sort("applied_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def list_applications_by_company_stage(
    company_id: str,
    stage_id: str,
    job_id: Optional[str] = None
) -> List[dict]:
    """List applications by company and stage (for pipeline board)."""
    query: Dict[str, Any] = {
        "company_id": ObjectId(company_id),
        "current_stage_id": stage_id,
        "status": STATUS_ACTIVE
    }
    if job_id:
        query["job_id"] = ObjectId(job_id)
    
    cursor = applications_collection().find(query).sort("updated_at", -1)
    return await cursor.to_list(length=200)


async def move_application_stage(
    application_id: str,
    new_stage_id: str,
    new_stage_name: str,
    changed_by: str,
    reason: str,
    student_visible_stage: Optional[str] = None
) -> Optional[dict]:
    """Move an application to a new stage."""
    now = datetime.utcnow()
    
    stage_entry = {
        "stage_id": new_stage_id,
        "stage_name": new_stage_name,
        "changed_by": changed_by,
        "timestamp": now,
        "reason": reason
    }
    
    update = {
        "$set": {
            "current_stage_id": new_stage_id,
            "current_stage_name": new_stage_name,
            "updated_at": now
        },
        "$push": {
            "stage_history": stage_entry
        }
    }
    
    if student_visible_stage:
        update["$set"]["student_visible_stage"] = student_visible_stage
    
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        update
    )
    return await get_application(application_id)


async def update_application_status(
    application_id: str,
    status: str,
    changed_by: str
) -> Optional[dict]:
    """Update the overall application status."""
    now = datetime.utcnow()
    
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$set": {
                "status": status,
                "updated_at": now
            },
            "$push": {
                "stage_history": {
                    "stage_id": None,
                    "stage_name": f"Status: {status}",
                    "changed_by": changed_by,
                    "timestamp": now,
                    "reason": f"Status changed to {status}"
                }
            }
        }
    )
    return await get_application(application_id)


async def add_interview_to_application(application_id: str, interview_id: str) -> Optional[dict]:
    """Link an interview to an application."""
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$addToSet": {"interview_ids": ObjectId(interview_id)},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    return await get_application(application_id)


async def set_offer_on_application(application_id: str, offer_id: str) -> Optional[dict]:
    """Link an offer to an application."""
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$set": {
                "offer_id": ObjectId(offer_id),
                "updated_at": datetime.utcnow()
            }
        }
    )
    return await get_application(application_id)


async def add_note_to_application(
    application_id: str,
    author_id: str,
    author_name: str,
    content: str,
    is_private: bool = True
) -> Optional[dict]:
    """Add a note to an application."""
    note = {
        "id": str(ObjectId()),
        "author_id": author_id,
        "author_name": author_name,
        "content": content,
        "is_private": is_private,
        "created_at": datetime.utcnow()
    }
    
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$push": {"notes": note},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    return await get_application(application_id)


async def add_tags_to_application(application_id: str, tags: List[str]) -> Optional[dict]:
    """Add tags to an application."""
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$addToSet": {"tags": {"$each": tags}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    return await get_application(application_id)


async def remove_tag_from_application(application_id: str, tag: str) -> Optional[dict]:
    """Remove a tag from an application."""
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$pull": {"tags": tag},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    return await get_application(application_id)


async def update_rating_summary(
    application_id: str,
    overall_score: float,
    scorecard_count: int
) -> Optional[dict]:
    """Update the aggregated rating summary."""
    await applications_collection().update_one(
        {"_id": ObjectId(application_id)},
        {
            "$set": {
                "rating_summary.overall_score": overall_score,
                "rating_summary.scorecard_count": scorecard_count,
                "rating_summary.last_updated": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    return await get_application(application_id)


async def get_pipeline_board_stats(company_id: str, job_id: Optional[str] = None) -> Dict[str, int]:
    """Get count of applications per stage for pipeline board."""
    match_stage: Dict[str, Any] = {
        "company_id": ObjectId(company_id),
        "status": STATUS_ACTIVE
    }
    if job_id:
        match_stage["job_id"] = ObjectId(job_id)
    
    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$current_stage_id", "count": {"$sum": 1}}}
    ]
    
    cursor = applications_collection().aggregate(pipeline)
    results = await cursor.to_list(length=100)
    return {r["_id"]: r["count"] for r in results}


async def ensure_application_indexes():
    """Create indexes for applications collection."""
    col = applications_collection()
    
    # Unique constraint: one application per job+student
    await col.create_index(
        [("job_id", 1), ("student_id", 1)],
        unique=True
    )
    
    # Pipeline board queries
    await col.create_index([("company_id", 1), ("current_stage_id", 1)])
    await col.create_index([("job_id", 1), ("current_stage_id", 1)])
    
    # Student queries
    await col.create_index([("student_id", 1), ("status", 1)])
    
    # General
    await col.create_index("applied_at")
    await col.create_index("updated_at")
