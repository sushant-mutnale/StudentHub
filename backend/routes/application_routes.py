"""
Application Routes - API endpoints for application tracking.

Recruiter endpoints:
- View applications, move stages, add notes/tags

Student endpoints:
- View my applications, timeline, withdraw
"""

from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import application as application_model
from ..models import pipeline as pipeline_model
from ..models import user as user_model
from ..models import job as job_model
from ..schemas.application_schema import (
    StageMoveRequest,
    AddNoteRequest,
    AddTagsRequest,
    WithdrawRequest,
    ApplicationResponse,
    ApplicationListResponse,
    StudentApplicationResponse,
    StudentApplicationsListResponse,
    StageHistoryEntry,
    ApplicationNote,
    TimelineEvent,
    ApplicationTimelineResponse,
)
from ..utils.dependencies import get_current_user, get_current_recruiter, get_current_student

router = APIRouter(prefix="/applications", tags=["applications"])


def serialize_application(app: dict, job: dict = None, student: dict = None) -> ApplicationResponse:
    """Convert MongoDB application document to response model."""
    return ApplicationResponse(
        id=str(app["_id"]),
        job_id=str(app["job_id"]),
        job_title=job.get("title") if job else None,
        company_id=str(app["company_id"]),
        company_name=job.get("company_name") if job else None,
        student_id=str(app["student_id"]),
        student_name=student.get("full_name") if student else None,
        current_stage_id=app["current_stage_id"],
        current_stage_name=app["current_stage_name"],
        student_visible_stage=app.get("student_visible_stage", app["current_stage_name"]),
        status=app["status"],
        stage_history=[
            StageHistoryEntry(
                stage_id=h.get("stage_id"),
                stage_name=h["stage_name"],
                changed_by=h["changed_by"],
                timestamp=h["timestamp"],
                reason=h.get("reason")
            ) for h in app.get("stage_history", [])
        ],
        interview_count=len(app.get("interview_ids", [])),
        has_offer=app.get("offer_id") is not None,
        tags=app.get("tags", []),
        notes=[
            ApplicationNote(
                id=n["id"],
                author_id=n["author_id"],
                author_name=n["author_name"],
                content=n["content"],
                is_private=n.get("is_private", True),
                created_at=n["created_at"]
            ) for n in app.get("notes", [])
        ],
        overall_score=app.get("rating_summary", {}).get("overall_score"),
        applied_at=app["applied_at"],
        updated_at=app["updated_at"]
    )


def serialize_student_application(app: dict, job: dict) -> StudentApplicationResponse:
    """Convert to student-facing application response."""
    return StudentApplicationResponse(
        id=str(app["_id"]),
        job_id=str(app["job_id"]),
        job_title=job.get("title", "Unknown"),
        company_name=job.get("company_name", "Unknown"),
        current_stage=app.get("student_visible_stage", "Under Review"),
        status=app["status"],
        applied_at=app["applied_at"],
        last_updated=app["updated_at"],
        interview_count=len(app.get("interview_ids", [])),
        has_offer=app.get("offer_id") is not None
    )


# ============ RECRUITER ENDPOINTS ============

@router.get("/job/{job_id}", response_model=ApplicationListResponse)
async def list_job_applications(
    job_id: str,
    stage_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    recruiter=Depends(get_current_recruiter)
):
    """List all applications for a specific job."""
    # Verify job ownership
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    
    apps = await application_model.list_applications_for_job(
        job_id=job_id,
        stage_id=stage_id,
        status=status,
        limit=limit,
        skip=skip
    )
    
    # Enrich with student info
    results = []
    for app in apps:
        student = await user_model.get_user_by_id(str(app["student_id"]))
        results.append(serialize_application(app, job, student))
    
    return ApplicationListResponse(
        applications=results,
        total=len(results)
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user=Depends(get_current_user)
):
    """Get a specific application by ID."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    user_id = str(current_user["_id"])
    is_student = str(app["student_id"]) == user_id
    is_recruiter = str(app["company_id"]) == user_id
    
    if not is_student and not is_recruiter:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    job = await job_model.get_job(str(app["job_id"]))
    student = await user_model.get_user_by_id(str(app["student_id"]))
    
    response = serialize_application(app, job, student)
    
    # Filter private notes for students
    if is_student:
        response.notes = [n for n in response.notes if not n.is_private]
    
    return response


@router.put("/{application_id}/stage", response_model=ApplicationResponse)
async def move_application_stage(
    application_id: str,
    payload: StageMoveRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Move an application to a different pipeline stage."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Verify ownership
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get pipeline and validate transition
    pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
    if not pipeline:
        raise HTTPException(status_code=400, detail="Pipeline not found")
    
    # Validate transition is allowed
    if not pipeline_model.can_transition(
        pipeline, 
        app["current_stage_id"], 
        payload.new_stage_id, 
        "recruiter"
    ):
        raise HTTPException(status_code=400, detail="Transition not allowed")
    
    # Get new stage info
    new_stage = pipeline_model.get_stage_by_id(pipeline, payload.new_stage_id)
    if not new_stage:
        raise HTTPException(status_code=400, detail="Invalid stage")
    
    # Perform the move
    updated = await application_model.move_application_stage(
        application_id=application_id,
        new_stage_id=payload.new_stage_id,
        new_stage_name=new_stage["name"],
        changed_by=str(recruiter["_id"]),
        reason=payload.reason,
        student_visible_stage=payload.student_visible_stage or new_stage.get("student_visible_name")
    )
    
    # Update status if terminal stage
    if new_stage["type"] in pipeline_model.TERMINAL_STAGE_TYPES:
        status_map = {
            "hired": application_model.STATUS_HIRED,
            "rejected": application_model.STATUS_REJECTED,
            "withdrawn": application_model.STATUS_WITHDRAWN
        }
        new_status = status_map.get(new_stage["type"], application_model.STATUS_ARCHIVED)
        await application_model.update_application_status(
            application_id, new_status, str(recruiter["_id"])
        )
        updated = await application_model.get_application(application_id)
    
    job = await job_model.get_job(str(app["job_id"]))
    student = await user_model.get_user_by_id(str(app["student_id"]))
    
    return serialize_application(updated, job, student)


@router.post("/{application_id}/notes", response_model=ApplicationResponse)
async def add_application_note(
    application_id: str,
    payload: AddNoteRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Add a note to an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    recruiter_name = recruiter.get("company_name") or recruiter.get("username", "Recruiter")
    
    updated = await application_model.add_note_to_application(
        application_id=application_id,
        author_id=str(recruiter["_id"]),
        author_name=recruiter_name,
        content=payload.content,
        is_private=payload.is_private
    )
    
    job = await job_model.get_job(str(app["job_id"]))
    student = await user_model.get_user_by_id(str(app["student_id"]))
    
    return serialize_application(updated, job, student)


@router.post("/{application_id}/tags", response_model=ApplicationResponse)
async def add_application_tags(
    application_id: str,
    payload: AddTagsRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Add tags to an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    updated = await application_model.add_tags_to_application(
        application_id, payload.tags
    )
    
    job = await job_model.get_job(str(app["job_id"]))
    student = await user_model.get_user_by_id(str(app["student_id"]))
    
    return serialize_application(updated, job, student)


@router.delete("/{application_id}/tags/{tag}")
async def remove_application_tag(
    application_id: str,
    tag: str,
    recruiter=Depends(get_current_recruiter)
):
    """Remove a tag from an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await application_model.remove_tag_from_application(application_id, tag)
    return {"status": "removed", "tag": tag}


# ============ STUDENT ENDPOINTS ============

@router.get("/my", response_model=StudentApplicationsListResponse)
async def list_my_applications(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    student=Depends(get_current_student)
):
    """List all applications for the current student."""
    apps = await application_model.list_applications_for_student(
        student_id=str(student["_id"]),
        status=status,
        limit=limit
    )
    
    results = []
    for app in apps:
        job = await job_model.get_job(str(app["job_id"]))
        if job:
            results.append(serialize_student_application(app, job))
    
    return StudentApplicationsListResponse(
        applications=results,
        total=len(results)
    )


@router.get("/{application_id}/timeline", response_model=ApplicationTimelineResponse)
async def get_application_timeline(
    application_id: str,
    current_user=Depends(get_current_user)
):
    """Get the activity timeline for an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    user_id = str(current_user["_id"])
    is_student = str(app["student_id"]) == user_id
    is_recruiter = str(app["company_id"]) == user_id
    
    if not is_student and not is_recruiter:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    job = await job_model.get_job(str(app["job_id"]))
    
    # Build timeline events from stage history
    events = []
    for i, entry in enumerate(app.get("stage_history", [])):
        events.append(TimelineEvent(
            id=f"stage_{i}",
            event_type="stage_change",
            title=f"Moved to {entry['stage_name']}",
            description=entry.get("reason"),
            timestamp=entry["timestamp"],
            data={"stage_id": entry.get("stage_id")}
        ))
    
    # Sort by timestamp descending
    events.sort(key=lambda e: e.timestamp, reverse=True)
    
    return ApplicationTimelineResponse(
        application_id=application_id,
        job_title=job.get("title", "Unknown") if job else "Unknown",
        company_name=job.get("company_name", "Unknown") if job else "Unknown",
        events=events
    )


@router.post("/{application_id}/withdraw", response_model=StudentApplicationResponse)
async def withdraw_application(
    application_id: str,
    payload: WithdrawRequest,
    student=Depends(get_current_student)
):
    """Withdraw an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["student_id"]) != str(student["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if app["status"] != application_model.STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="Application is not active")
    
    # Get pipeline to find withdrawn stage
    pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
    withdrawn_stage = pipeline_model.get_stage_by_type(pipeline, "withdrawn")
    
    if withdrawn_stage:
        await application_model.move_application_stage(
            application_id=application_id,
            new_stage_id=withdrawn_stage["id"],
            new_stage_name=withdrawn_stage["name"],
            changed_by=str(student["_id"]),
            reason=payload.reason or "Student withdrew application",
            student_visible_stage="Withdrawn"
        )
    
    await application_model.update_application_status(
        application_id,
        application_model.STATUS_WITHDRAWN,
        str(student["_id"])
    )
    
    updated = await application_model.get_application(application_id)
    job = await job_model.get_job(str(app["job_id"]))
    
    return serialize_student_application(updated, job)
