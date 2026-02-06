"""
Admin Routes - Administrative tools for verification and moderation.

Endpoints for:
- Review queue (flagged jobs/recruiters)
- Approve/reject jobs
- Verify/suspend recruiters
- Audit trail viewing
"""

from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..database import get_database
from ..models import audit as audit_model
from ..services import moderation_service
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response models
class JobActionRequest(BaseModel):
    reason: Optional[str] = None


class RecruiterActionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ReviewQueueItem(BaseModel):
    id: str
    type: str  # job or recruiter
    title: str
    company_name: Optional[str]
    risk_score: int
    flags: List[dict]
    created_at: datetime
    status: str


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    action: str
    entity_type: str
    entity_id: str
    actor_type: str
    reason: Optional[str]


def users_collection():
    return get_database()["users"]


def jobs_collection():
    return get_database()["jobs"]


async def require_admin(current_user=Depends(get_current_user)):
    """Dependency to require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ============ DASHBOARD STATS ============

@router.get("/stats")
async def get_admin_stats(admin=Depends(require_admin)):
    """Get admin dashboard statistics."""
    users_count = await users_collection().count_documents({})
    jobs_count = await jobs_collection().count_documents({})
    recruiters_count = await users_collection().count_documents({"role": "recruiter"})
    students_count = await users_collection().count_documents({"role": "student"})
    pending_jobs = await jobs_collection().count_documents({"status": "pending_review"})
    
    return {
        "users": users_count,
        "jobs": jobs_count,
        "recruiters": recruiters_count,
        "students": students_count,
        "pending_jobs": pending_jobs
    }


@router.get("/moderation")
async def get_moderation_queue_alias(
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin)
):
    """Get moderation queue - alias for review queue."""
    items = []
    
    # Get flagged jobs
    job_cursor = jobs_collection().find({
        "status": {"$in": ["pending_review", "flagged"]}
    }).sort("created_at", -1).limit(limit)
    
    async for job in job_cursor:
        moderation = job.get("moderation", {})
        items.append({
            "id": str(job["_id"]),
            "type": "job",
            "title": job.get("title", "Untitled"),
            "risk_score": moderation.get("risk_score", 0),
            "created_at": job.get("created_at"),
            "status": job.get("status", "unknown")
        })
    
    return items


# ============ REVIEW QUEUE ============

@router.get("/review-queue")
async def get_review_queue(
    type_filter: Optional[str] = Query(None, description="job or recruiter"),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin)
):
    """Get items pending admin review."""
    items = []
    
    # Get flagged jobs
    if type_filter is None or type_filter == "job":
        job_cursor = jobs_collection().find({
            "status": moderation_service.JOB_STATUS_PENDING_REVIEW
        }).sort("created_at", -1).limit(limit)
        
        async for job in job_cursor:
            moderation = job.get("moderation", {})
            recruiter = await users_collection().find_one({"_id": job.get("recruiter_id")})
            
            items.append(ReviewQueueItem(
                id=str(job["_id"]),
                type="job",
                title=job.get("title", "Untitled"),
                company_name=recruiter.get("company_name") if recruiter else None,
                risk_score=moderation.get("risk_score", 0),
                flags=moderation.get("flags", []),
                created_at=job.get("created_at", datetime.utcnow()),
                status=job.get("status", "unknown")
            ))
    
    # Get flagged recruiters
    if type_filter is None or type_filter == "recruiter":
        recruiter_cursor = users_collection().find({
            "role": "recruiter",
            "verification_status": moderation_service.VERIFICATION_REVIEW_REQUIRED
        }).sort("created_at", -1).limit(limit)
        
        async for recruiter in recruiter_cursor:
            items.append(ReviewQueueItem(
                id=str(recruiter["_id"]),
                type="recruiter",
                title=recruiter.get("company_name", recruiter.get("username", "Unknown")),
                company_name=recruiter.get("company_name"),
                risk_score=0,
                flags=[],
                created_at=recruiter.get("created_at", datetime.utcnow()),
                status=recruiter.get("verification_status", "unknown")
            ))
    
    return {"items": items, "total": len(items)}


# ============ JOB MODERATION ============

@router.post("/jobs/{job_id}/approve")
async def approve_job(
    job_id: str,
    admin=Depends(require_admin)
):
    """Approve a job for publishing."""
    job = await jobs_collection().find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await jobs_collection().update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": moderation_service.JOB_STATUS_PUBLISHED,
                "moderation.reviewed_by": str(admin["_id"]),
                "moderation.reviewed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    await audit_model.log_audit(
        action=audit_model.ACTION_JOB_APPROVED,
        entity_type="job",
        entity_id=job_id,
        actor_id=str(admin["_id"]),
        actor_type=audit_model.ACTOR_ADMIN
    )
    
    return {"message": "Job approved", "status": "published"}


@router.post("/jobs/{job_id}/reject")
async def reject_job(
    job_id: str,
    payload: JobActionRequest,
    admin=Depends(require_admin)
):
    """Reject a job with reason."""
    job = await jobs_collection().find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await jobs_collection().update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": moderation_service.JOB_STATUS_REJECTED,
                "moderation.reviewed_by": str(admin["_id"]),
                "moderation.reviewed_at": datetime.utcnow(),
                "moderation.rejection_reason": payload.reason,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    await audit_model.log_audit(
        action=audit_model.ACTION_JOB_REJECTED,
        entity_type="job",
        entity_id=job_id,
        actor_id=str(admin["_id"]),
        actor_type=audit_model.ACTOR_ADMIN,
        reason=payload.reason
    )
    
    return {"message": "Job rejected", "reason": payload.reason}


# ============ RECRUITER MODERATION ============

@router.post("/recruiters/{recruiter_id}/verify")
async def verify_recruiter(
    recruiter_id: str,
    admin=Depends(require_admin)
):
    """Manually verify a recruiter."""
    recruiter = await users_collection().find_one({"_id": ObjectId(recruiter_id)})
    if not recruiter or recruiter.get("role") != "recruiter":
        raise HTTPException(status_code=404, detail="Recruiter not found")
    
    await users_collection().update_one(
        {"_id": ObjectId(recruiter_id)},
        {
            "$set": {
                "verification_status": moderation_service.VERIFICATION_VERIFIED,
                "verification_data.verified_at": datetime.utcnow(),
                "verification_data.verified_by": str(admin["_id"]),
                "updated_at": datetime.utcnow()
            }
        }
    )
    

    
    # Audit Log
    from ..services.audit_service import audit_service, AuditAction
    await audit_service.log_event(
        action=AuditAction.VERIFY,
        entity_type="user",
        entity_id=recruiter_id,
        actor_id=str(admin["_id"]),
        changes={"verification_status": moderation_service.VERIFICATION_VERIFIED}
    )

    return {"message": "Recruiter verified"}


@router.put("/recruiters/{recruiter_id}/verify")
async def verify_recruiter_put(
    recruiter_id: str,
    admin=Depends(require_admin)
):
    """PUT alias for verify_recruiter (backwards compatibility)."""
    return await verify_recruiter(recruiter_id=recruiter_id, admin=admin)


@router.post("/recruiters/{recruiter_id}/suspend")
async def suspend_recruiter(
    recruiter_id: str,
    payload: RecruiterActionRequest,
    admin=Depends(require_admin)
):
    """Suspend a recruiter account."""
    recruiter = await users_collection().find_one({"_id": ObjectId(recruiter_id)})
    if not recruiter or recruiter.get("role") != "recruiter":
        raise HTTPException(status_code=404, detail="Recruiter not found")
    
    await users_collection().update_one(
        {"_id": ObjectId(recruiter_id)},
        {
            "$set": {
                "verification_status": moderation_service.VERIFICATION_SUSPENDED,
                "suspension_reason": payload.reason,
                "suspended_at": datetime.utcnow(),
                "suspended_by": str(admin["_id"]),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Also close all their active jobs
    await jobs_collection().update_many(
        {"recruiter_id": ObjectId(recruiter_id), "status": {"$nin": ["closed", "rejected"]}},
        {"$set": {"status": "closed", "updated_at": datetime.utcnow()}}
    )
    
    await audit_model.log_audit(
        action=audit_model.ACTION_RECRUITER_SUSPENDED,
        entity_type="recruiter",
        entity_id=recruiter_id,
        actor_id=str(admin["_id"]),
        actor_type=audit_model.ACTOR_ADMIN,
        reason=payload.reason
    )
    
    return {"message": "Recruiter suspended", "reason": payload.reason}


@router.post("/recruiters/{recruiter_id}/unsuspend")
async def unsuspend_recruiter(
    recruiter_id: str,
    admin=Depends(require_admin)
):
    """Unsuspend a recruiter account."""
    recruiter = await users_collection().find_one({"_id": ObjectId(recruiter_id)})
    if not recruiter or recruiter.get("role") != "recruiter":
        raise HTTPException(status_code=404, detail="Recruiter not found")
    
    if recruiter.get("verification_status") != moderation_service.VERIFICATION_SUSPENDED:
        raise HTTPException(status_code=400, detail="Recruiter is not suspended")
    
    await users_collection().update_one(
        {"_id": ObjectId(recruiter_id)},
        {
            "$set": {
                "verification_status": moderation_service.VERIFICATION_VERIFIED,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "suspension_reason": "",
                "suspended_at": "",
                "suspended_by": ""
            }
        }
    )
    
    await audit_model.log_audit(
        action=audit_model.ACTION_RECRUITER_UNSUSPENDED,
        entity_type="recruiter",
        entity_id=recruiter_id,
        actor_id=str(admin["_id"]),
        actor_type=audit_model.ACTOR_ADMIN
    )
    
    return {"message": "Recruiter unsuspended"}


# ============ AUDIT LOGS ============

@router.get("/audit/{entity_type}/{entity_id}")
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin)
):
    """Get audit trail for a specific entity."""
    logs = await audit_model.get_audit_logs_for_entity(entity_type, entity_id, limit)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "logs": [
            AuditLogEntry(
                id=str(log["_id"]),
                timestamp=log["timestamp"],
                action=log["action"],
                entity_type=log["entity_type"],
                entity_id=log["entity_id"],
                actor_type=log.get("actor_type", "user"),
                reason=log.get("reason")
            )
            for log in logs
        ],
        "total": len(logs)
    }


@router.get("/audit/recent")
async def get_recent_audit_logs(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    admin=Depends(require_admin)
):
    """Get recent audit logs."""
    logs = await audit_model.get_recent_audit_logs(
        limit=limit,
        entity_type=entity_type
    )
    
    return {
        "logs": [
            AuditLogEntry(
                id=str(log["_id"]),
                timestamp=log["timestamp"],
                action=log["action"],
                entity_type=log["entity_type"],
                entity_id=log["entity_id"],
                actor_type=log.get("actor_type", "user"),
                reason=log.get("reason")
            )
            for log in logs
        ],
        "total": len(logs)
    }
