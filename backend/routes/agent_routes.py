"""
Multi-Agent Interview Routes
API endpoints for AI-powered interview simulation using multiple agents.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..interview_engine.compatibility.agent_interview import (
    LegacyAnswerRequest,
    LegacyEndRequest,
    LegacyFeedbackRequest,
    LegacyHintRequest,
    LegacyResumeRequest,
    LegacyStartRequest,
    answer_idempotency_key,
    end_command_id,
    to_answer_response,
    to_end_response,
    to_feedback_response,
    to_hint_response,
    to_resume_response,
    to_start_response,
)
from ..interview_engine.compatibility.dependencies import engine_dependency
from ..interview_engine.contracts.messages import (
    EndSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from ..interview_engine.errors import DeviceConflict, EngineError
from ..services.multi_agent_system import multi_agent_interview
from ..services.resume_parser import resume_parser
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/agent-interview", tags=["multi-agent-interview"])


def _handle(exc: EngineError):
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, **exc.details},
    )


def _require_device(device_id):
    if not device_id:
        raise HTTPException(status_code=400, detail={"code": "device_id_required"})


# ============ Helper Logic ============

@router.post("/extract-text")
async def extract_resume_text(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    Extract raw text from a PDF resume for interview personalization.
    Does not save the file permanently.
    """
    import tempfile
    import os
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    try:
        content = await file.read()
        # open in binary mode
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode='wb') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            text, _ = resume_parser.extract_text(tmp_path)
            if not text:
                raise HTTPException(status_code=422, detail="Could not extract text from PDF")
            return {"text": text, "filename": file.filename}
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_interview(
    body: LegacyStartRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.start(
            StartSessionCommand(
                candidate_id=str(current_user["_id"]),
                interview_type=body.interview_type,
                mode=body.mode,
                device_id=body.device_id,
                client_request_id=body.request_id or uuid.uuid4().hex,
                role=body.role,
                company=body.company,
            )
        )
    except EngineError as exc:
        _handle(exc)
    response = to_start_response(result)
    response["request_id"] = body.request_id or response["request_id"]
    return response


@router.post("/answer")
async def submit_answer(
    body: LegacyAnswerRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.submit_turn(
            SubmitTurnCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                turn_idempotency_key=answer_idempotency_key(
                    str(current_user["_id"]), body.session_id, body.request_id, body.answer
                ),
                kind=body.kind,
                text=body.answer,
                question_id=body.question_id,
            )
        )
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        view = await engine.session_view(record)
    except EngineError as exc:
        _handle(exc)
    response = to_answer_response(result, view)
    response["turn_request_id"] = body.request_id
    return response


@router.post("/hint")
async def request_hint(
    body: LegacyHintRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        question_id = record.current_question_id or ""
        result = await engine.request_hint(
            RequestHintCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                hint_idempotency_key=f"{current_user['_id']}:{body.session_id}:{question_id}",
                question_id=question_id or None,
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_hint_response(result)


@router.post("/end")
async def end_interview(
    body: LegacyEndRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.end(
            EndSessionCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                end_command_id=end_command_id(
                    str(current_user["_id"]), body.session_id, body.end_request_id
                ),
                reason="candidate_completed",
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_end_response(result)


@router.post("/feedback")
async def get_feedback(
    body: LegacyFeedbackRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        if record.device_id != body.device_id:
            raise DeviceConflict()
        report = await engine.get_report(str(current_user["_id"]), record.report_id)
    except EngineError as exc:
        _handle(exc)
    if report.outcome == "evaluating":
        await engine.drain_outbox()
        report = await engine.get_report(str(current_user["_id"]), record.report_id)
    body_dict = report.body
    if report.outcome == "ready" and body_dict is None:
        body_dict = await engine.build_report_body(report.report_id)
    return to_feedback_response(report, body_dict)


@router.post("/resume")
async def resume_interview(
    body: LegacyResumeRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.resume(
            ResumeSessionCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                command_id=body.command_id,
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_resume_response(result)


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


# ============ Voice Interview Helpers ============

async def start_agent_interview_logic(
    student_id: str,
    company: str,
    role: str,
    difficulty: str,
    interview_type: str = "mixed",
    resume_text: str = ""
) -> dict:
    """Helper logic to start a multi-agent interview (used by voice_routes or other client channels)."""
    from datetime import datetime
    from ..database import get_database
    
    session_id = str(uuid.uuid4())
    result = await multi_agent_interview.start(
        session_id=session_id,
        student_id=student_id,
        company=company,
        role=role,
        difficulty=difficulty,
        interview_type=interview_type,
        resume_text=resume_text
    )
    
    # Save the session to MongoDB agent_interviews collection
    db = get_database()
    await db.agent_interviews.insert_one({
        "session_id": session_id,
        "student_id": student_id,
        "company": company,
        "role": role,
        "difficulty": difficulty,
        "interview_type": interview_type,
        "status": "active",
        "questions_answered": 0,
        "hints_used": 0,
        "created_at": datetime.utcnow()
    })
    
    return {
        "session_id": session_id,
        "interviewer_message": result.get("question", "")
    }


async def submit_answer_logic(
    session_id: str,
    answer: str
) -> dict:
    """Helper logic to submit an answer and advance the multi-agent session state."""
    from ..database import get_database
    
    db = get_database()
    agent_doc = await db.agent_interviews.find_one({"session_id": session_id})
    if not agent_doc:
        return {"error": "Session not found", "status": "failed"}

    result = await multi_agent_interview.answer(session_id, answer)
    if "error" in result:
        return {"error": result["error"], "status": "failed"}
        
    # Increment questions answered in MongoDB
    new_count = agent_doc.get("questions_answered", 0) + 1
    update_data = {"questions_answered": new_count}
    
    # If the coordinator returned empty next_question or dsa_stage is completed, mark session as completed
    status = "active"
    next_question = result.get("next_question", "")
    dsa_stage = result.get("dsa_stage")
    
    # If no next question or dsa_stage is completed/empty
    if next_question == "" or dsa_stage == "completed":
        status = "completed"
        update_data["status"] = "completed"
        
    await db.agent_interviews.update_one(
        {"session_id": session_id},
        {"$set": update_data}
    )
    
    return {
        "status": status,
        "evaluation": result.get("evaluation"),
        "next_question": next_question,
        "dsa_stage": dsa_stage
    }


async def end_agent_interview_logic(
    session_id: str
) -> dict:
    """Helper logic to end a multi-agent interview and get the final evaluation/coaching."""
    from ..database import get_database
    
    db = get_database()
    result = await multi_agent_interview.finish(session_id)
    
    # Map 'coaching' to 'career_coaching' for compatibility with voice_routes
    result["career_coaching"] = result.get("coaching", "")
    
    # Update MongoDB status to completed
    await db.agent_interviews.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )
    
    return result
