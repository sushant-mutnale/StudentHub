"""
Scorecard Routes - API endpoints for scorecard management.

Recruiter endpoints:
- Create/list scorecard templates
- Submit evaluations
- View aggregations
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import scorecard as scorecard_model
from ..models import application as application_model
from ..models import user as user_model
from ..schemas.scorecard_schema import (
    ScorecardTemplateCreateRequest,
    ScorecardTemplateResponse,
    ScorecardTemplateListResponse,
    ScorecardSubmitRequest,
    ScorecardResponse,
    ScorecardListResponse,
    ScorecardAggregation,
)
from ..utils.dependencies import get_current_user, get_current_recruiter

router = APIRouter(prefix="/scorecards", tags=["scorecards"])


def serialize_template(doc: dict) -> ScorecardTemplateResponse:
    """Convert MongoDB template document to response."""
    return ScorecardTemplateResponse(
        id=str(doc["_id"]),
        company_id=str(doc["company_id"]),
        name=doc["name"],
        stage_type=doc["stage_type"],
        interview_type=doc.get("interview_type"),
        criteria=doc.get("criteria", []),
        pass_threshold=doc.get("pass_threshold", 3.5),
        is_default=doc.get("is_default", False),
        created_at=doc.get("created_at", datetime.utcnow())
    )


def serialize_scorecard(doc: dict, template: dict = None, evaluator: dict = None) -> ScorecardResponse:
    """Convert MongoDB scorecard document to response."""
    return ScorecardResponse(
        id=str(doc["_id"]),
        application_id=str(doc["application_id"]),
        stage_id=doc["stage_id"],
        interview_id=str(doc["interview_id"]) if doc.get("interview_id") else None,
        template_id=str(doc["template_id"]),
        template_name=template.get("name") if template else None,
        evaluator_id=str(doc["evaluator_id"]),
        evaluator_name=evaluator.get("company_name") or evaluator.get("full_name") if evaluator else None,
        scores=doc.get("scores", []),
        overall_score=doc.get("overall_score", 0),
        decision=doc.get("decision", "hold"),
        overall_notes=doc.get("overall_notes"),
        rejection_reason=doc.get("rejection_reason"),
        submitted_at=doc.get("submitted_at", datetime.utcnow())
    )


# ============ TEMPLATE ENDPOINTS ============

@router.get("/templates", response_model=ScorecardTemplateListResponse)
async def list_templates(
    stage_type: Optional[str] = Query(None),
    interview_type: Optional[str] = Query(None),
    recruiter=Depends(get_current_recruiter)
):
    """List scorecard templates for the company."""
    company_id = str(recruiter["_id"])
    
    templates = await scorecard_model.list_scorecard_templates(
        company_id=company_id,
        stage_type=stage_type,
        interview_type=interview_type
    )
    
    # Create defaults if none exist
    if not templates:
        templates = await scorecard_model.create_default_templates_for_company(company_id)
    
    return ScorecardTemplateListResponse(
        templates=[serialize_template(t) for t in templates],
        total=len(templates)
    )


@router.post("/templates", response_model=ScorecardTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: ScorecardTemplateCreateRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Create a custom scorecard template."""
    company_id = str(recruiter["_id"])
    
    template = await scorecard_model.create_scorecard_template(
        company_id=company_id,
        name=payload.name,
        stage_type=payload.stage_type,
        criteria=[c.dict() for c in payload.criteria],
        interview_type=payload.interview_type,
        pass_threshold=payload.pass_threshold
    )
    
    return serialize_template(template)


@router.get("/templates/{template_id}", response_model=ScorecardTemplateResponse)
async def get_template(
    template_id: str,
    recruiter=Depends(get_current_recruiter)
):
    """Get a specific template by ID."""
    template = await scorecard_model.get_scorecard_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Verify ownership
    if str(template["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return serialize_template(template)


@router.post("/templates/init")
async def initialize_templates(recruiter=Depends(get_current_recruiter)):
    """Initialize default templates for the company."""
    company_id = str(recruiter["_id"])
    
    existing = await scorecard_model.list_scorecard_templates(company_id)
    if existing:
        return {"message": "Templates already exist", "count": len(existing)}
    
    templates = await scorecard_model.create_default_templates_for_company(company_id)
    return {"message": "Default templates created", "count": len(templates)}


# ============ SCORECARD SUBMISSION ============

@router.post("/applications/{application_id}", response_model=ScorecardResponse, status_code=status.HTTP_201_CREATED)
async def submit_scorecard(
    application_id: str,
    payload: ScorecardSubmitRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Submit a scorecard evaluation for an application."""
    # Verify application exists and belongs to this company
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        scorecard = await scorecard_model.submit_scorecard(
            application_id=application_id,
            stage_id=payload.stage_id,
            template_id=payload.template_id,
            evaluator_id=str(recruiter["_id"]),
            scores=[s.dict() for s in payload.scores],
            decision=payload.decision,
            overall_notes=payload.overall_notes,
            rejection_reason=payload.rejection_reason,
            interview_id=payload.interview_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update application rating summary
    agg = await scorecard_model.get_scorecard_aggregation(application_id)
    if agg["average_score"] is not None:
        await application_model.update_rating_summary(
            application_id,
            agg["average_score"],
            agg["count"]
        )
    
    template = await scorecard_model.get_scorecard_template(payload.template_id)
    return serialize_scorecard(scorecard, template, recruiter)


@router.get("/applications/{application_id}", response_model=ScorecardListResponse)
async def list_scorecards(
    application_id: str,
    current_user=Depends(get_current_user)
):
    """Get all scorecards for an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    user_id = str(current_user["_id"])
    is_recruiter = str(app["company_id"]) == user_id
    
    if not is_recruiter:
        raise HTTPException(status_code=403, detail="Only recruiters can view scorecards")
    
    scorecards = await scorecard_model.get_scorecards_for_application(application_id)
    
    results = []
    for sc in scorecards:
        template = await scorecard_model.get_scorecard_template(str(sc["template_id"]))
        evaluator = await user_model.get_user_by_id(str(sc["evaluator_id"]))
        results.append(serialize_scorecard(sc, template, evaluator))
    
    return ScorecardListResponse(
        scorecards=results,
        total=len(results)
    )


@router.get("/applications/{application_id}/aggregation", response_model=ScorecardAggregation)
async def get_aggregation(
    application_id: str,
    recruiter=Depends(get_current_recruiter)
):
    """Get aggregated scorecard stats for an application."""
    app = await application_model.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if str(app["company_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    agg = await scorecard_model.get_scorecard_aggregation(application_id)
    return ScorecardAggregation(**agg)
