"""
AI Planner Routes
API endpoints for AI-powered study plan creation and management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.ai_planner_agent import ai_planner
from ..services.gap_analysis_service import gap_analyzer
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/planner", tags=["ai-planner"])


# ============ Request/Response Models ============

class CreatePlanRequest(BaseModel):
    """Request to create a study plan."""
    target_company: str = Field(..., description="Company to prepare for")
    target_role: str = Field(default="Software Engineer")
    prep_weeks: int = Field(default=8, ge=1, le=24)
    hours_per_day: float = Field(default=2.0, ge=0.5, le=8)
    preferred_days: Optional[List[str]] = None
    resume_skills: Optional[List[str]] = Field(default=None, description="Skills from resume")
    target_skills: Optional[List[str]] = Field(default=None, description="Skills needed for role")


class MarkTaskRequest(BaseModel):
    """Request to mark a task complete."""
    day_number: int
    task_index: int


class AdjustPlanRequest(BaseModel):
    """Request to adjust a plan."""
    new_hours_per_day: Optional[float] = None
    extend_weeks: Optional[int] = None
    skip_days: Optional[List[str]] = None


# ============ Create Plan ============

@router.post("/create")
async def create_study_plan(
    payload: CreatePlanRequest,
    current_user=Depends(get_current_user)
):
    """
    Create a personalized AI-generated study plan.
    
    Uses:
    - Gap analysis to identify weak areas
    - Company interview patterns
    - LLM to generate optimal schedule
    
    Returns week-by-week plan with daily tasks.
    """
    student_id = str(current_user["_id"])
    
    # Get or create gap analysis
    gaps = {}
    if payload.resume_skills and payload.target_skills:
        gap_result = await gap_analyzer.analyze_gaps(
            resume_skills=payload.resume_skills,
            target_skills=payload.target_skills
        )
        gaps = gap_result
    else:
        # Use stored gap analysis if available
        gaps = {"missing_skills": ["Data Structures", "Algorithms", "System Design"]}
    
    result = await ai_planner.create_study_plan(
        student_id=student_id,
        gaps=gaps,
        target_company=payload.target_company,
        target_role=payload.target_role,
        prep_weeks=payload.prep_weeks,
        hours_per_day=payload.hours_per_day,
        preferred_days=payload.preferred_days
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create plan"))
    
    return result


# ============ Get Today's Tasks ============

@router.get("/today/{plan_id}")
async def get_today_tasks(
    plan_id: str,
    current_user=Depends(get_current_user)
):
    """Get today's study tasks."""
    result = await ai_planner.get_today_tasks(plan_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# ============ Mark Task Complete ============

@router.post("/complete/{plan_id}")
async def mark_task_complete(
    plan_id: str,
    payload: MarkTaskRequest,
    current_user=Depends(get_current_user)
):
    """Mark a specific task as completed."""
    result = await ai_planner.mark_task_complete(
        plan_id=plan_id,
        day_number=payload.day_number,
        task_index=payload.task_index
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ============ Get Progress ============

@router.get("/progress/{plan_id}")
async def get_plan_progress(
    plan_id: str,
    current_user=Depends(get_current_user)
):
    """Get overall progress for a study plan."""
    result = await ai_planner.get_progress(plan_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# ============ Adjust Plan ============

@router.put("/adjust/{plan_id}")
async def adjust_plan(
    plan_id: str,
    payload: AdjustPlanRequest,
    current_user=Depends(get_current_user)
):
    """Adjust an existing study plan."""
    result = await ai_planner.adjust_plan(
        plan_id=plan_id,
        new_hours_per_day=payload.new_hours_per_day,
        extend_weeks=payload.extend_weeks,
        skip_days=payload.skip_days
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ============ List My Plans ============

@router.get("/my-plans")
async def get_my_plans(current_user=Depends(get_current_user)):
    """Get all study plans for the current user."""
    student_id = str(current_user["_id"])
    plans = await ai_planner.get_student_plans(student_id)
    
    return {
        "status": "success",
        "plans": plans,
        "total": len(plans)
    }


# ============ Quick Plan (Demo) ============

@router.post("/quick")
async def quick_plan(
    company: str = "Amazon",
    weeks: int = 4,
    current_user=Depends(get_current_user)
):
    """Create a quick 4-week plan (simplified)."""
    student_id = str(current_user["_id"])
    
    result = await ai_planner.create_study_plan(
        student_id=student_id,
        gaps={"missing_skills": ["DSA", "System Design"]},
        target_company=company,
        target_role="Software Engineer",
        prep_weeks=weeks,
        hours_per_day=2.0
    )
    
    return result
