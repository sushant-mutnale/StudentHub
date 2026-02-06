"""
Interview Session Routes
API endpoints for interview session lifecycle management.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_database
from ..services.interview_orchestrator import interview_orchestrator, SessionStatus
from ..schemas.session_schema import (
    StartSessionRequest,
    CreateSessionResponse,
    RoundPreview,
    StartSessionResponse,
    QuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    Evaluation,
    NextAction,
    SessionStatusResponse,
    InterviewRound,
    InterviewReportResponse,
    RoundBreakdown,
    QAItem,
    SessionListItem,
    MySessionsResponse,
)
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/sessions", tags=["interview-sessions"])


def sessions_collection():
    return get_database()["interview_sessions"]


# ============ Create Session ============

@router.post("/create", response_model=CreateSessionResponse)
async def create_session(
    payload: StartSessionRequest,
    current_user=Depends(get_current_user)
):
    """
    Create a new interview session.
    
    Initializes session with company interview pattern.
    Call /start to begin the interview.
    """
    student_id = str(current_user["_id"])
    
    # Get parsed resume if provided
    parsed_resume = None
    if payload.resume_id:
        resumes = get_database()["resume_uploads"]
        resume_doc = await resumes.find_one({"_id": ObjectId(payload.resume_id)})
        if resume_doc:
            parsed_resume = resume_doc.get("parsed_data", {})
    
    # Parse JD if provided
    parsed_jd = None
    if payload.jd_text:
        from ..services.jd_parser import jd_parser
        jd_result = await jd_parser.parse_jd(payload.jd_text)
        if jd_result.get("success"):
            parsed_jd = jd_result
    
    result = await interview_orchestrator.create_session(
        student_id=student_id,
        company=payload.company,
        role=payload.role,
        resume_id=payload.resume_id,
        jd_text=payload.jd_text,
        parsed_jd=parsed_jd,
        parsed_resume=parsed_resume
    )
    
    return CreateSessionResponse(
        session_id=result["session_id"],
        company=result["company"],
        role=result["role"],
        total_rounds=result["total_rounds"],
        rounds_preview=[RoundPreview(**r) for r in result["rounds_preview"]],
        estimated_duration_minutes=result["estimated_duration_minutes"],
        message="Session created. Call /start to begin."
    )


# ============ Start Session ============

@router.post("/{session_id}/start", response_model=StartSessionResponse)
async def start_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Start an interview session.
    Returns the first question.
    """
    # Verify ownership
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await interview_orchestrator.start_session(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return StartSessionResponse(
        session_id=session_id,
        current_round=result["current_round"],
        first_question=result["first_question"],
        message=result.get("message", "Interview started!")
    )


# ============ Get Next Question ============

@router.get("/{session_id}/next-question", response_model=QuestionResponse)
async def get_next_question(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get the next question in the interview.
    """
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await interview_orchestrator.get_next_question(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    if result.get("interview_completed"):
        return QuestionResponse(
            question_id="",
            round="",
            round_num=-1,
            question_type="",
            difficulty="",
            question="",
            interview_completed=True
        )
    
    return QuestionResponse(
        question_id=result["question_id"],
        round=result["round"],
        round_num=result["round_num"],
        question_type=result["question_type"],
        difficulty=result["difficulty"],
        question=result["question"],
        hints=result.get("hints", []),
        time_limit_seconds=result.get("time_limit_seconds", 1800),
        questions_in_round=result.get("questions_in_round", 0),
        interview_completed=False
    )


# ============ Submit Answer ============

@router.post("/{session_id}/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user=Depends(get_current_user)
):
    """
    Submit an answer for evaluation.
    
    Returns:
    - Evaluation with score and feedback
    - Next action (next question, next round, or complete)
    """
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await interview_orchestrator.submit_answer(
        session_id=session_id,
        question_id=payload.question_id,
        answer=payload.answer,
        time_taken_seconds=payload.time_taken_seconds,
        code=payload.code
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    eval_data = result["evaluation"]
    next_data = result["next_action"]
    
    return SubmitAnswerResponse(
        evaluation=Evaluation(
            score=eval_data.get("score", 0),
            feedback=eval_data.get("feedback", ""),
            strengths=eval_data.get("strengths", []),
            improvements=eval_data.get("improvements", [])
        ),
        next_action=NextAction(
            action=next_data.get("action", "next_question"),
            message=next_data.get("message", ""),
            next_round=next_data.get("next_round"),
            next_round_type=next_data.get("next_round_type"),
            questions_remaining=next_data.get("questions_remaining")
        ),
        new_difficulty=result.get("new_difficulty", "medium")
    )


# ============ Get Session Status ============

@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Get current status of a session."""
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rounds = [
        InterviewRound(
            round_num=r["round_num"],
            type=r["type"],
            name=r["name"],
            duration_minutes=r.get("duration_minutes", 60),
            questions_answered=r.get("questions_answered", 0),
            score=r.get("score", 0),
            status=r.get("status", "pending")
        )
        for r in session["rounds"]
    ]
    
    return SessionStatusResponse(
        session_id=session_id,
        session_status=session["status"],
        company=session["company"],
        role=session["role"],
        current_round=session["current_round"],
        total_rounds=session["total_rounds"],
        total_questions_answered=session.get("total_questions_answered", 0),
        overall_score=session.get("overall_score", 0),
        rounds=rounds
    )


# ============ Get Report ============

@router.get("/{session_id}/report", response_model=InterviewReportResponse)
async def get_interview_report(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get the full interview report.
    Only available after interview is completed.
    """
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    report = await interview_orchestrator.generate_report(session_id)
    
    if "error" in report:
        raise HTTPException(status_code=400, detail=report["error"])
    
    return InterviewReportResponse(
        session_id=report["session_id"],
        company=report["company"],
        role=report["role"],
        overall_score=report["overall_score"],
        total_questions=report["total_questions"],
        total_time_minutes=report["total_time_minutes"],
        started_at=report.get("started_at"),
        completed_at=report.get("completed_at"),
        round_breakdown=[RoundBreakdown(**rb) for rb in report["round_breakdown"]],
        questions_and_answers=[QAItem(**qa) for qa in report["questions_and_answers"]],
        strengths=report["strengths"],
        areas_to_improve=report["areas_to_improve"],
        recommendations=report["recommendations"]
    )


# ============ List My Sessions ============

@router.get("/my-sessions", response_model=MySessionsResponse)
async def get_my_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user=Depends(get_current_user)
):
    """Get all interview sessions for the current user."""
    student_id = str(current_user["_id"])
    
    query = {"student_id": ObjectId(student_id)}
    if status:
        query["status"] = status
    
    cursor = sessions_collection().find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=50)
    
    sessions = [
        SessionListItem(
            session_id=str(doc["_id"]),
            company=doc["company"],
            role=doc["role"],
            status=doc["status"],
            overall_score=doc.get("overall_score", 0),
            total_rounds=doc["total_rounds"],
            created_at=doc["created_at"]
        )
        for doc in docs
    ]
    
    return MySessionsResponse(
        sessions=sessions,
        total=len(sessions)
    )


# ============ Pause/Resume Session ============

@router.post("/{session_id}/pause")
async def pause_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Pause an in-progress session."""
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if session["status"] != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session is not in progress")
    
    await sessions_collection().update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"status": SessionStatus.PAUSED, "updated_at": datetime.utcnow()}}
    )
    
    return {"status": "success", "message": "Session paused"}


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Resume a paused session."""
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if session["status"] != SessionStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Session is not paused")
    
    await sessions_collection().update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"status": SessionStatus.IN_PROGRESS, "updated_at": datetime.utcnow()}}
    )
    
    # Get next question
    next_q = await interview_orchestrator.get_next_question(session_id)
    
    return {
        "status": "success",
        "message": "Session resumed",
        "next_question": next_q
    }


# ============ Abandon Session ============

@router.post("/{session_id}/abandon")
async def abandon_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """Abandon/cancel an interview session."""
    session = await interview_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["student_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if session["status"] == SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot abandon completed session")
    
    await sessions_collection().update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "status": SessionStatus.ABANDONED,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"status": "success", "message": "Session abandoned"}
