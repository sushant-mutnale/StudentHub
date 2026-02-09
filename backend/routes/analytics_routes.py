from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from ..database import get_database
from ..utils.dependencies import get_current_user
from ..events.handlers.analytics_handler import get_funnel_metrics, get_conversion_rates

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Helper to ensure ObjectId
def to_oid(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id_str)

@router.get("/student/overview")
async def get_student_analytics(current_user=Depends(get_current_user)):
    """
    Get analytics overview for a student.
    - Application Status Breakdown
    - Recent Activity
    """
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    
    db = get_database()
    student_id = str(current_user["_id"])
    
    # 1. Application Status Breakdown
    pipeline = [
        {"$match": {"student_id": ObjectId(student_id)}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    app_stats = await db.applications.aggregate(pipeline).to_list(None)
    
    application_summary = {
        "applied": 0,
        "interviewing": 0,
        "offered": 0,
        "rejected": 0,
        "total": 0
    }
    
    # Map statuses to summary categories
    status_map = {
        "applied": "applied",
        "under_review": "applied",
        "interview_scheduled": "interviewing",
        "interview_completed": "interviewing",
        "technical_interview": "interviewing",
        "hr_interview": "interviewing",
        "offer_extended": "offered",
        "offer_accepted": "offered",
        "hired": "offered",
        "rejected": "rejected",
        "declined": "rejected"
    }
    
    for stat in app_stats:
        status = stat["_id"]
        count = stat["count"]
        category = status_map.get(status, "applied")
        application_summary[category] += count
        application_summary["total"] += count

    # 2. Recent Activity (from analytics_events)
    recent_activity = await db.analytics_events.find(
        {"user_id": student_id}
    ).sort("timestamp", -1).limit(10).to_list(None)
    
    # Format activity
    formatted_activity = []
    for event in recent_activity:
        formatted_activity.append({
            "type": event["event_type"],
            "description": _format_activity_description(event),
            "timestamp": event["timestamp"]
        })

    return {
        "applications": application_summary,
        "recent_activity": formatted_activity,
        # Placeholder for skill gaps if we want to add it later
        "skill_gaps": []
    }

def _format_activity_description(event: dict) -> str:
    """Helper to create readable descriptions for events."""
    etype = event["event_type"]
    meta = event.get("metadata", {})
    
    if etype == "job.viewed":
        return "Viewed a job"
    elif etype == "job.saved":
        return "Saved a job"
    elif etype == "application.created":
        return "Applied to a job"
    elif etype == "interview.scheduled":
        return "Interview scheduled"
    elif etype == "offer.extended":
        return "Received an offer!"
    
    return etype.replace(".", " ").capitalize()

@router.get("/recruiter/overview")
async def get_recruiter_analytics(current_user=Depends(get_current_user)):
    """
    Get analytics overview for a recruiter.
    - Active Jobs
    - Total Applicants
    - Upcoming Interviews
    """
    if current_user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter access required")
    
    db = get_database()
    recruiter_id = ObjectId(current_user["_id"])
    
    # 1. Job Stats
    active_jobs = await db.jobs.count_documents(
        {"recruiter_id": recruiter_id, "status": "active"}
    )
    total_jobs = await db.jobs.count_documents(
        {"recruiter_id": recruiter_id}
    )
    
    # 2. Total Applicants (across all recruiter's jobs)
    # Get all job IDs first
    recruiters_jobs = await db.jobs.find(
        {"recruiter_id": recruiter_id}, {"_id": 1}
    ).to_list(None)
    job_ids = [str(j["_id"]) for j in recruiters_jobs]
    
    total_applications = await db.applications.count_documents(
        {"job_id": {"$in": job_ids}}
    )
    
    # 3. Active Interviews
    active_interviews = await db.interviews.count_documents(
        {
            "recruiter_id": recruiter_id,
            "status": {"$in": ["scheduled", "rescheduled", "proposed"]}
        }
    )
    
    # 4. Job Performance (Quick list)
    # Get top 5 active jobs with applicant counts
    pipeline = [
        {"$match": {"recruiter_id": recruiter_id, "status": "active"}},
        {"$lookup": {
            "from": "applications",
            "localField": "_id",
            "foreignField": "job_id_obj", # Usually applications store job_id as string, need to check schema
            # If job_id is string in apps, looking up by _id (ObjectId) won't work directly unless we convert.
            # Let's assume applications.job_id is string for now based on typical patterns here.
            "pipeline": [{"$project": {"_id": 1}}], # Minimal projection
            "as": "apps"
        }},
        {"$project": {
            "title": 1,
            "posted_at": 1,
            "applicant_count": {"$size": "$apps"} # This lookup might fail if types mismatch
        }},
        {"$limit": 5}
    ]
    
    # Alternative for Job Performance: Fetch jobs, then count apps manually to be safe on types
    recent_jobs = await db.jobs.find(
        {"recruiter_id": recruiter_id, "status": "active"}
    ).sort("posted_at", -1).limit(5).to_list(None)
    
    job_performance = []
    for job in recent_jobs:
        app_count = await db.applications.count_documents({"job_id": str(job["_id"])})
        job_performance.append({
            "id": str(job["_id"]),
            "title": job["title"],
            "posted_at": job["posted_at"],
            "applicants": app_count,
            "views": 0 # TODO: Get views from analytics
        })
        
        # Hydrate views from analytics
        funnel = await get_funnel_metrics(str(job["_id"]))
        job_performance[-1]["views"] = funnel["views"]

    return {
        "active_jobs": active_jobs,
        "total_jobs": total_jobs,
        "total_applicants": total_applications,
        "active_interviews": active_interviews,
        "job_performance": job_performance
    }

@router.get("/recruiter/job/{job_id}/funnel")
async def get_job_funnel(job_id: str, current_user=Depends(get_current_user)):
    """
    Get detailed funnel metrics for a specific job.
    """
    if current_user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter access required")
        
    # Verify job ownership
    db = get_database()
    job = await db.jobs.find_one({"_id": ObjectId(job_id), "recruiter_id": ObjectId(current_user["_id"])})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")
        
    metrics = await get_funnel_metrics(job_id)
    rates = await get_conversion_rates(job_id)
    
    return {
        "job_title": job["title"],
        "metrics": metrics,
        "conversion_rates": rates
    }
