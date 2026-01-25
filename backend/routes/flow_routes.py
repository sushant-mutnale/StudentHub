"""
Interview Flow Routes
Unified API endpoints for the complete interview experience.
Connects all Module 3 components with Module 1/2 integration.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.interview_flow import interview_flow
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/interview-flow", tags=["interview-flow"])


# ============ Request/Response Models ============

class StartInterviewRequest(BaseModel):
    """Request to start a full interview."""
    company: str = Field(..., description="Company name, e.g., Amazon, Google")
    role: str = Field(default="Software Engineer", description="Role, e.g., SDE-2")
    resume_id: Optional[str] = Field(default=None, description="ID of uploaded resume")
    jd_text: Optional[str] = Field(default=None, description="Job description text")


class QuickStartRequest(BaseModel):
    """Request for quick demo interview."""
    company: str = Field(default="Amazon")
    difficulty: str = Field(default="medium")


# ============ Start Full Interview ============

@router.post("/start")
async def start_full_interview(
    payload: StartInterviewRequest,
    current_user=Depends(get_current_user)
):
    """
    Start a complete interview flow.
    
    This unified endpoint:
    1. Parses/retrieves resume
    2. Parses JD
    3. Fetches company knowledge
    4. Creates and starts interview session
    5. Returns first question
    
    Use this for the complete experience.
    """
    student_id = str(current_user["_id"])
    
    result = await interview_flow.start_full_interview(
        student_id=student_id,
        company=payload.company,
        role=payload.role,
        resume_id=payload.resume_id,
        jd_text=payload.jd_text
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to start interview"))
    
    return result


@router.post("/quick-start")
async def quick_start_interview(
    payload: QuickStartRequest,
    current_user=Depends(get_current_user)
):
    """
    Quick start an interview without resume/JD.
    Good for practice sessions.
    """
    student_id = str(current_user["_id"])
    
    result = await interview_flow.quick_start_demo(
        student_id=student_id,
        company=payload.company,
        difficulty=payload.difficulty
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to start"))
    
    return result


# ============ Complete Interview ============

@router.post("/complete/{session_id}")
async def complete_interview(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Complete an interview and update profile.
    
    This endpoint:
    1. Generates final report
    2. Updates AI profile with interview score
    3. Updates overall score
    4. Logs completion activity
    5. Updates matching score for recruiters
    """
    result = await interview_flow.complete_interview_and_update_profile(session_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete"))
    
    return result


# ============ Statistics ============

@router.get("/stats")
async def get_interview_stats(current_user=Depends(get_current_user)):
    """
    Get comprehensive interview statistics.
    
    Returns:
    - Total interviews completed
    - Average score
    - Companies practiced
    - Skill breakdown
    - Improvement trend
    """
    student_id = str(current_user["_id"])
    stats = await interview_flow.get_student_interview_stats(student_id)
    return {"status": "success", "stats": stats}


# ============ Diagnostics ============

@router.get("/health")
async def check_health(current_user=Depends(get_current_user)):
    """
    Check health of all interview flow components.
    Useful for debugging and monitoring.
    """
    student_id = str(current_user["_id"])
    result = await interview_flow.validate_flow(student_id)
    return result


# ============ Demo Endpoints (No Auth) ============

@router.get("/demo/companies")
async def get_demo_companies():
    """Get list of companies available for demo interviews."""
    from ..data.company_interview_data import COMPANY_INTERVIEW_DATA
    
    companies = [
        {
            "name": c["company"],
            "difficulty": c.get("difficulty", "medium"),
            "rounds": len(c.get("rounds", []))
        }
        for c in COMPANY_INTERVIEW_DATA
    ]
    
    return {"status": "success", "companies": companies}


@router.get("/demo/flow-status")
async def get_flow_status():
    """Check if interview flow services are available (no auth)."""
    try:
        from ..services.interview_orchestrator import interview_orchestrator
        from ..services.question_generator import question_generator
        from ..services.answer_evaluator import answer_evaluator
        
        return {
            "status": "success",
            "services": {
                "orchestrator": interview_orchestrator is not None,
                "question_generator": question_generator is not None,
                "answer_evaluator": answer_evaluator is not None
            },
            "message": "Interview system is operational"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
