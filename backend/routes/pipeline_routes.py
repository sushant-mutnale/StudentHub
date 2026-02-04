"""
Pipeline Routes - API endpoints for managing hiring pipelines.

Recruiter endpoints:
- Create/update pipeline templates
- View pipeline board per job
- Manage stage configurations
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import pipeline as pipeline_model
from ..models import application as application_model
from ..models import user as user_model
from ..models import job as job_model
from ..schemas.pipeline_schema import (
    PipelineCreateRequest,
    PipelineUpdateRequest,
    PipelineResponse,
    PipelineListResponse,
    PipelineBoardResponse,
    PipelineBoardColumn,
    PipelineBoardCandidate,
)
from ..utils.dependencies import get_current_user, get_current_recruiter

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def serialize_pipeline(doc: dict) -> PipelineResponse:
    """Convert MongoDB pipeline document to response model."""
    return PipelineResponse(
        id=str(doc["_id"]),
        company_id=str(doc["company_id"]),
        name=doc["name"],
        version=doc["version"],
        active=doc["active"],
        is_default=doc.get("is_default", False),
        stages=doc.get("stages", []),
        transitions=doc.get("transitions", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    payload: PipelineCreateRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Create a new pipeline template for the company."""
    company_id = str(recruiter["_id"])
    
    # Generate stage IDs if not provided
    stages = []
    for i, stage in enumerate(payload.stages):
        stage_data = dict(stage)
        if "id" not in stage_data:
            stage_data["id"] = str(ObjectId())
        if "order" not in stage_data:
            stage_data["order"] = i + 1
        stages.append(stage_data)
    
    # Generate default transitions if not provided
    transitions = payload.transitions
    if not transitions:
        transitions = pipeline_model.generate_default_transitions(stages)
    
    try:
        doc = await pipeline_model.create_pipeline_template(
            company_id=company_id,
            name=payload.name,
            stages=stages,
            transitions=transitions,
            created_by=company_id
        )
        return serialize_pipeline(doc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=PipelineListResponse)
async def list_pipelines(
    include_inactive: bool = Query(False),
    recruiter=Depends(get_current_recruiter)
):
    """List all pipeline templates for the company."""
    company_id = str(recruiter["_id"])
    pipelines = await pipeline_model.list_company_pipelines(company_id)
    
    if not include_inactive:
        pipelines = [p for p in pipelines if p.get("active", False)]
    
    return PipelineListResponse(
        pipelines=[serialize_pipeline(p) for p in pipelines],
        total=len(pipelines)
    )


@router.get("/active", response_model=PipelineResponse)
async def get_active_pipeline(recruiter=Depends(get_current_recruiter)):
    """Get the currently active pipeline template for the company."""
    company_id = str(recruiter["_id"])
    
    pipeline = await pipeline_model.get_active_pipeline(company_id)
    if not pipeline:
        # Create default pipeline if none exists
        company_name = recruiter.get("company_name", "Company")
        pipeline = await pipeline_model.create_default_pipeline_for_company(
            company_id, company_name
        )
    
    return serialize_pipeline(pipeline)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    recruiter=Depends(get_current_recruiter)
):
    """Get a specific pipeline template by ID."""
    pipeline = await pipeline_model.get_pipeline_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Verify ownership
    if str(pipeline["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return serialize_pipeline(pipeline)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    payload: PipelineUpdateRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Update a pipeline template (creates a new version)."""
    pipeline = await pipeline_model.get_pipeline_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    if str(pipeline["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    updates = {}
    if payload.stages is not None:
        updates["stages"] = payload.stages
    if payload.transitions is not None:
        updates["transitions"] = payload.transitions
    
    try:
        updated = await pipeline_model.update_pipeline_template(
            pipeline_id=pipeline_id,
            updates=updates,
            updated_by=str(recruiter["_id"])
        )
        return serialize_pipeline(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pipeline_id}/board/{job_id}", response_model=PipelineBoardResponse)
async def get_pipeline_board(
    pipeline_id: str,
    job_id: str,
    recruiter=Depends(get_current_recruiter)
):
    """Get the pipeline board view for a specific job (kanban-style)."""
    # Verify pipeline ownership
    pipeline = await pipeline_model.get_pipeline_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    if str(pipeline["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify job ownership
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get applications grouped by stage
    columns = []
    total_candidates = 0
    
    for stage in sorted(pipeline.get("stages", []), key=lambda s: s.get("order", 0)):
        stage_id = stage["id"]
        
        # Get applications in this stage
        apps = await application_model.list_applications_by_company_stage(
            company_id=str(recruiter["_id"]),
            stage_id=stage_id,
            job_id=job_id
        )
        
        # Enrich with student info
        candidates = []
        for app in apps:
            student = await user_model.get_user_by_id(str(app["student_id"]))
            if student:
                candidates.append(PipelineBoardCandidate(
                    application_id=str(app["_id"]),
                    student_id=str(app["student_id"]),
                    student_name=student.get("full_name") or student.get("username", "Unknown"),
                    student_avatar=student.get("avatar_url"),
                    applied_at=app["applied_at"],
                    last_activity=app.get("updated_at"),
                    overall_score=app.get("rating_summary", {}).get("overall_score"),
                    tags=app.get("tags", [])
                ))
        
        columns.append(PipelineBoardColumn(
            stage_id=stage_id,
            stage_name=stage["name"],
            stage_type=stage["type"],
            color=stage.get("color", "#3b82f6"),
            order=stage.get("order", 0),
            candidates=candidates,
            count=len(candidates)
        ))
        total_candidates += len(candidates)
    
    return PipelineBoardResponse(
        job_id=job_id,
        job_title=job.get("title", "Unknown Job"),
        pipeline_id=pipeline_id,
        pipeline_name=pipeline["name"],
        columns=columns,
        total_candidates=total_candidates
    )


@router.post("/init", response_model=PipelineResponse)
async def initialize_default_pipeline(recruiter=Depends(get_current_recruiter)):
    """Initialize the default pipeline for a company (if none exists)."""
    company_id = str(recruiter["_id"])
    
    existing = await pipeline_model.get_active_pipeline(company_id)
    if existing:
        return serialize_pipeline(existing)
    
    company_name = recruiter.get("company_name", "Company")
    pipeline = await pipeline_model.create_default_pipeline_for_company(
        company_id, company_name
    )
    return serialize_pipeline(pipeline)
