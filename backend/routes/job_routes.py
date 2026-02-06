from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import job as job_model
from ..models import application as application_model
from ..models import pipeline as pipeline_model
from ..schemas.job_schema import (
    JobApplicationCreate,
    JobApplicationResponse,
    JobCreate,
    JobResponse,
)
from ..utils.dependencies import get_current_recruiter, get_current_student, get_current_user
from ..utils.activity_logger import log_activity

router = APIRouter()


def db_job_to_public(db_job: dict) -> JobResponse:
    """Convert MongoDB job document to JobResponse with string IDs."""
    return JobResponse(
        id=str(db_job.get("_id") or db_job.get("id")),
        recruiter_id=str(db_job.get("recruiter_id")),
        title=db_job.get("title"),
        description=db_job.get("description"),
        skills_required=db_job.get("skills_required", []),
        location=db_job.get("location"),
        created_at=db_job.get("created_at"),
        visibility=db_job.get("visibility", "public"),
        company_name=db_job.get("company_name"),
    )


def db_application_to_public(doc: dict) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=str(doc.get("_id") or doc.get("id")),
        job_id=str(doc.get("job_id")),
        student_id=str(doc.get("student_id")),
        student_name=doc.get("student_name"),
        student_username=doc.get("student_username"),
        message=doc.get("message", ""),
        resume_url=doc.get("resume_url"),
        created_at=doc.get("created_at"),
    )


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, recruiter=Depends(get_current_recruiter)):
    doc = await job_model.create_job(recruiter, payload.dict())
    await log_activity(
        str(recruiter["_id"]), 
        "JOB_CREATED", 
        {"job_id": str(doc["_id"]), "title": doc.get("title")}
    )
    return db_job_to_public(doc)


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    q: str | None = Query(default=None, description="Search in job title and description"),
    skills: str | None = Query(
        default=None,
        description="Comma-separated skills to match (e.g. React,Node,SQL)",
    ),
    location: str | None = Query(
        default=None, description="Location filter (partial, case-insensitive)"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
):
    skills_list = (
        [s.strip() for s in skills.split(",") if s.strip()] if skills is not None else None
    )
    jobs = await job_model.list_jobs_for_user(
        current_user,
        q=q,
        skills=skills_list,
        location=location,
        limit=limit,
        skip=skip,
    )
    return [db_job_to_public(job) for job in jobs]


@router.get("/my", response_model=list[JobResponse])
async def my_jobs(recruiter=Depends(get_current_recruiter)):
    jobs = await job_model.list_jobs_by_recruiter(str(recruiter["_id"]))
    return [db_job_to_public(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, current_user=Depends(get_current_user)):
    job = await job_model.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Enforce visibility for student users: they should not be able to fetch
    # non-public jobs directly by ID.
    if current_user.get("role") == "student":
        visibility = job.get("visibility", "public")
        if visibility != "public":
             raise HTTPException(status_code=403, detail="Access denied to non-public job")
             
    return db_job_to_public(job)


@router.get("/{job_id}/pipeline")
async def get_job_pipeline(job_id: str, recruiter=Depends(get_current_recruiter)):
    """Get pipeline view for a job's applications."""
    try:
        from bson import ObjectId
        # Verify job belongs to recruiter
        job = await job_model.jobs_collection().find_one({
            "_id": ObjectId(job_id),
            "recruiter_id": recruiter["_id"]
        })
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")
        
        # Get applications for this job
        applications = await application_model.list_applications_for_job(job_id)
        
        return {
            "job_id": job_id,
            "job_title": job.get("title"),
            "applications": [db_application_to_public(app) for app in applications],
            "total": len(applications)
        }
    except Exception as e:
         # Handle invalid ID format
         if "ObjectId" in str(e):
             raise HTTPException(status_code=404, detail="Invalid job ID")
         raise e



@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_job(
    job_id: str,
    payload: JobApplicationCreate,
    current_student=Depends(get_current_student),
):
    """Allow a student to apply to a job."""
    # Get job to extract company info
    job = await job_model.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    app_doc = await job_model.create_job_application(job_id, current_student, payload.dict())
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application failed")
    
    # Create ATS application record (Module 5)
    recruiter_id = str(job["recruiter_id"])
    pipeline = await pipeline_model.get_active_pipeline(recruiter_id)
    
    if not pipeline:
        # Create default pipeline for this company
        company_name = job.get("company_name", "Company")
        pipeline = await pipeline_model.create_default_pipeline_for_company(
            recruiter_id, company_name
        )
    
    # Get the "Applied" stage
    applied_stage = pipeline_model.get_stage_by_type(pipeline, "applied")
    if applied_stage:
        try:
            await application_model.create_application(
                job_id=job_id,
                student_id=str(current_student["_id"]),
                company_id=recruiter_id,
                pipeline_template_id=str(pipeline["_id"]),
                pipeline_version=pipeline["version"],
                initial_stage_id=applied_stage["id"],
                initial_stage_name=applied_stage["name"]
            )
        except Exception:
            # Application record might already exist (duplicate apply)
            pass
    
    await log_activity(
        str(current_student["_id"]), 
        "JOB_APPLIED", 
        {"job_id": job_id}
    )
    return db_application_to_public(app_doc)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str, 
    payload: JobCreate, 
    recruiter=Depends(get_current_recruiter)
):
    """Update a job listing (requires ownership)."""
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found or not authorized")
        
    updated_job = await job_model.update_job(job_id, str(recruiter["_id"]), payload.dict())
    if not updated_job:
        raise HTTPException(status_code=404, detail="Update failed")
    return db_job_to_public(updated_job)


@router.get(
    "/{job_id}/applications",
    response_model=list[JobApplicationResponse],
)
async def list_job_applications(
    job_id: str, 
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    recruiter=Depends(get_current_recruiter)
):
    """Return all applications for a given job for the owning recruiter."""
    applications = await job_model.list_applications_for_job(
        job_id, 
        recruiter,
        limit=limit,
        skip=skip
    )
    if applications is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return [db_application_to_public(doc) for doc in applications]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, recruiter=Depends(get_current_recruiter)):
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    await job_model.delete_job(job_id, str(recruiter["_id"]))
    return {"status": "deleted"}

