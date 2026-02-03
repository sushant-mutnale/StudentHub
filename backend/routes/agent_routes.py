"""
Multi-Agent Interview Routes
API endpoints for AI-powered interview simulation using multiple agents.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import uuid

from ..services.multi_agent_system import multi_agent_interview
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/agent-interview", tags=["multi-agent-interview"])


# ============ Request/Response Models ============

class StartInterviewRequest(BaseModel):
    """Request to start a multi-agent interview."""
    company: str = Field(default="Tech Company", description="Target company")
    role: str = Field(default="Software Engineer", description="Target role")
    difficulty: str = Field(default="medium", description="Difficulty: easy, medium, hard")


class AnswerRequest(BaseModel):
    """Request to submit an answer."""
    session_id: str = Field(..., description="Interview session ID")
    answer: str = Field(..., min_length=1, description="Your answer")


class HintRequest(BaseModel):
    """Request for a hint."""
    session_id: str = Field(..., description="Interview session ID")
    level: int = Field(default=1, ge=1, le=3, description="Hint level: 1=small, 2=medium, 3=large")


class EndInterviewRequest(BaseModel):
    """Request to end interview."""
    session_id: str = Field(..., description="Interview session ID")


# ============ Start Interview ============

@router.post("/start")
async def start_interview(
    payload: StartInterviewRequest,
    current_user=Depends(get_current_user)
):
    """
    Start a new multi-agent interview session.
    
    The AI interviewer will greet you and ask the first question.
    """
    session_id = str(uuid.uuid4())
    student_id = str(current_user.get("_id", "demo_student"))
    
    try:
        result = await multi_agent_interview.start(
            session_id=session_id,
            student_id=student_id,
            company=payload.company,
            role=payload.role,
            difficulty=payload.difficulty
        )
        
        return {
            "status": "success",
            "session_id": session_id,
            "company": payload.company,
            "role": payload.role,
            "difficulty": payload.difficulty,
            "interviewer_message": result.get("question", ""),
            "instructions": [
                "Answer the question using POST /agent-interview/answer",
                "Request hints with POST /agent-interview/hint (reduces score)",
                "End session with POST /agent-interview/end"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


# ============ Submit Answer ============

@router.post("/answer")
async def submit_answer(
    payload: AnswerRequest,
    current_user=Depends(get_current_user)
):
    """
    Submit answer to current question.
    
    Returns evaluation and next question.
    """
    try:
        result = await multi_agent_interview.answer(
            session_id=payload.session_id,
            answer=payload.answer
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "status": "success",
            "session_id": payload.session_id,
            "evaluation": result.get("evaluation", {}),
            "next_question": result.get("next_question", ""),
            "agent_used": result.get("agent", "evaluator")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")


# ============ Request Hint ============

@router.post("/hint")
async def request_hint(
    payload: HintRequest,
    current_user=Depends(get_current_user)
):
    """
    Request a hint for the current question.
    
    Hints come in 3 levels:
    - Level 1: Small nudge (-5% score)
    - Level 2: Moderate hint (-10% score)
    - Level 3: Significant hint (-15% score)
    """
    try:
        result = await multi_agent_interview.hint(
            session_id=payload.session_id,
            level=payload.level
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "status": "success",
            "session_id": payload.session_id,
            "hint": result.get("hint", ""),
            "hint_level": result.get("hint_level", 1),
            "score_penalty": f"-{result.get('penalty', 0.05)*100:.0f}%",
            "total_hints_used": result.get("hints_used", 0),
            "agent_used": result.get("agent", "hint_provider")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hint: {str(e)}")


# ============ End Interview ============

@router.post("/end")
async def end_interview(
    payload: EndInterviewRequest,
    current_user=Depends(get_current_user)
):
    """
    End the interview session and get final results.
    
    Returns overall score, performance breakdown, and career coaching.
    """
    try:
        result = await multi_agent_interview.finish(payload.session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "status": "completed",
            "session_id": payload.session_id,
            "final_score": result.get("final_score", 0),
            "questions_answered": result.get("questions_answered", 0),
            "hints_used": result.get("hints_used", 0),
            "performance_breakdown": result.get("performance_breakdown", {}),
            "career_coaching": result.get("coaching", ""),
            "agent_used": result.get("agent", "career_coach")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end interview: {str(e)}")


# ============ Quick Demo ============

@router.post("/demo/start")
async def demo_start(
    company: str = "Google",
    role: str = "Software Engineer",
    difficulty: str = "medium"
):
    """
    Demo mode: Start interview without authentication.
    """
    session_id = f"demo_{uuid.uuid4().hex[:8]}"
    
    try:
        result = await multi_agent_interview.start(
            session_id=session_id,
            student_id="demo_user",
            company=company,
            role=role,
            difficulty=difficulty
        )
        
        return {
            "status": "demo_started",
            "session_id": session_id,
            "company": company,
            "interviewer_says": result.get("question", ""),
            "next_step": f"POST /agent-interview/demo/answer with session_id and your answer"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/demo/answer")
async def demo_answer(session_id: str, answer: str):
    """Demo mode: Submit answer without authentication."""
    try:
        result = await multi_agent_interview.answer(session_id, answer)
        
        if "error" in result:
            return {"status": "error", "message": result["error"]}
        
        return {
            "status": "success",
            "score": result.get("evaluation", {}).get("score", 0),
            "feedback": result.get("evaluation", {}).get("feedback", ""),
            "next_question": result.get("next_question", "")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/demo/hint")
async def demo_hint(session_id: str, level: int = 1):
    """Demo mode: Get hint without authentication."""
    try:
        result = await multi_agent_interview.hint(session_id, level)
        
        if "error" in result:
            return {"status": "error", "message": result["error"]}
        
        return {
            "status": "success",
            "hint": result.get("hint", ""),
            "penalty": result.get("penalty", 0.05)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/demo/end")
async def demo_end(session_id: str):
    """Demo mode: End interview without authentication."""
    try:
        result = await multi_agent_interview.finish(session_id)
        
        if "error" in result:
            return {"status": "error", "message": result["error"]}
        
        return {
            "status": "completed",
            "final_score": result.get("final_score", 0),
            "coaching": result.get("coaching", "")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============ Session Info ============

@router.get("/sessions")
async def get_active_sessions(current_user=Depends(get_current_user)):
    """Get list of active interview sessions."""
    sessions = multi_agent_interview.get_active_sessions()
    return {
        "status": "success",
        "active_sessions": len(sessions),
        "session_ids": sessions[:10]  # Limit to 10
    }


# ============ Agent Info ============

@router.get("/agents")
async def get_agent_info():
    """Get information about available agents."""
    return {
        "status": "success",
        "agents": [
            {
                "role": "interviewer",
                "name": "Alex the Interviewer",
                "description": "Conducts the interview, asks questions, provides follow-ups"
            },
            {
                "role": "evaluator",
                "name": "Eva the Evaluator",
                "description": "Evaluates answers, provides scores and feedback"
            },
            {
                "role": "hint_provider",
                "name": "Hannah the Hint Provider",
                "description": "Provides progressive hints when you're stuck"
            },
            {
                "role": "career_coach",
                "name": "Charlie the Career Coach",
                "description": "Gives career advice and end-of-interview coaching"
            },
            {
                "role": "coordinator",
                "name": "The Coordinator",
                "description": "Orchestrates all agents and manages interview flow"
            }
        ]
    }
