"""
Voice Interview Routes
Handles voice-based interview sessions with pre-recorded video states.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid

from ..utils.dependencies import get_current_user
from ..services.stt_service import transcribe_audio
from ..services.tts_service import text_to_speech
from ..services.interview_orchestrator import interview_orchestrator


router = APIRouter(prefix="/voice", tags=["Voice Interview"])


class VoiceSessionCreate(BaseModel):
    company: str
    role: str
    interview_type: str = "session"  # 'session' or 'agent'
    difficulty: Optional[str] = "medium"
    jd_text: Optional[str] = None
    resume_id: Optional[str] = None


class VoiceAnswerSubmit(BaseModel):
    session_id: str
    audio_transcription: Optional[str] = None  # If client-side transcription is done
    question_id: Optional[str] = None


class VoiceSessionResponse(BaseModel):
    status: str
    session_id: str
    interviewer_state: str  # 'asking', 'listening', 'thinking'
    audio_url: Optional[str] = None
    question_text: Optional[str] = None
    transcript: Optional[str] = None


@router.post("/session/create")
async def create_voice_session(
    data: VoiceSessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new voice interview session.
    Returns initial greeting with audio.
    """
    print(f"Voice Session Create Request: {data}")
    student_id = str(current_user["_id"])
    print(f"User ID: {student_id}")
    
    # Create session using existing orchestrator
    if data.interview_type == "session":
        session = await interview_orchestrator.create_session(
            student_id=student_id,
            company=data.company,
            role=data.role,
            jd_text=data.jd_text,
            resume_id=data.resume_id
        )
        session_id = session["session_id"]
        
        # Start session to get first question
        start_result = await interview_orchestrator.start_session(session_id)
        first_question_text = start_result["first_question"]["question"]
        
    else:  # agent interview
        from .agent_routes import start_agent_interview_logic
        session = await start_agent_interview_logic(
            student_id=student_id,
            company=data.company,
            role=data.role,
            difficulty=data.difficulty
        )
        session_id = session["session_id"]
        first_question_text = session["interviewer_message"]
    
    # Generate TTS for first question
    audio_url = await text_to_speech(first_question_text)
    
    return {
        "status": "success",
        "session_id": session_id,
        "interviewer_state": "asking",  # Start with asking state
        "audio_url": audio_url,
        "question_text": first_question_text,
        "message": "Voice interview session created. Avatar will ask the first question."
    }


@router.post("/answer/submit")
async def submit_voice_answer(
    session_id: str,
    audio_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit voice answer to a question.
    
    Flow:
    1. Transcribe audio (STT)
    2. Process answer through interview logic
    3. Generate next question (TTS)
    4. Return audio URL + state
    """
    print(f"Voice Answer Submit: Session ID: {session_id}")
    try:
        # Step 1: Transcribe audio
        audio_data = await audio_file.read()
        print(f"Audio received: {len(audio_data)} bytes")
        
        # Save to temp file for Whisper
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            transcription_result = await transcribe_audio(tmp_path)
            transcript = transcription_result if isinstance(transcription_result, str) else transcription_result.get("text", "")
        finally:
            import os
            os.unlink(tmp_path)
        
        if not transcript.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe audio. Please speak clearly.")
        
        # Step 2: Submit answer to interview logic
        # Check if it's a session or agent interview
        from ..database import get_database
        db = get_database()
        
        # Try to find in sessions first
        session_doc = await db.interview_sessions.find_one({"session_id": session_id})
        
        if session_doc:
            # Structured session interview
            # Get current question
            current_q = await db.interview_questions.find_one(
                {"session_id": session_id, "answered": False}
            )
            
            if not current_q:
                return {
                    "status": "completed",
                    "interviewer_state": "idle",
                    "message": "Interview completed!"
                }
            
            # Submit answer
            answer_result = await interview_orchestrator.submit_answer(
                session_id=session_id,
                question_id=str(current_q["_id"]),
                answer=transcript,
                time_taken_seconds=30  # Approximate
            )
            
            # Check if interview is done
            if answer_result["next_action"]["action"] in ["interview_completed", "next_round"]:
                completion_msg = "Great job! Interview completed."
                audio_url = await text_to_speech(completion_msg)
                
                return {
                    "status": "completed",
                    "interviewer_state": "asking",
                    "audio_url": audio_url,
                    "question_text": completion_msg,
                    "transcript": transcript,
                    "evaluation": answer_result["evaluation"]
                }
            
            # Get next question
            next_q = await interview_orchestrator.get_next_question(session_id)
            next_question_text = next_q["question"]
            
        else:
            # Agent interview
            agent_doc = await db.agent_interviews.find_one({"session_id": session_id})
            
            if not agent_doc:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Submit to agent
            from backend.routes.agent_routes import submit_answer_logic
            answer_result = await submit_answer_logic(
                session_id=session_id,
                answer=transcript
            )
            
            if answer_result.get("status") == "completed":
                completion_msg = "Interview completed. Thank you for your time!"
                audio_url = await text_to_speech(completion_msg)
                
                return {
                    "status": "completed",
                    "interviewer_state": "asking",
                    "audio_url": audio_url,
                    "question_text": completion_msg,
                    "transcript": transcript
                }
            
            next_question_text = answer_result.get("next_question", "Please continue.")
        
        # Step 3: Generate TTS for next question
        audio_url = await text_to_speech(next_question_text)
        
        return {
            "status": "success",
            "interviewer_state": "asking",
            "audio_url": audio_url,
            "question_text": next_question_text,
            "transcript": transcript,
            "evaluation": answer_result.get("evaluation")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/status")
async def get_voice_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current status of voice interview session."""
    from backend.database import get_database
    db = get_database()
    
    # Check sessions
    session = await db.interview_sessions.find_one({"session_id": session_id})
    
    if session:
        return {
            "status": session["session_status"],
            "current_round": session.get("current_round"),
            "questions_answered": session.get("total_questions_answered", 0),
            "overall_score": session.get("overall_score", 0)
        }
    
    # Check agent interviews
    agent = await db.agent_interviews.find_one({"session_id": session_id})
    
    if agent:
        return {
            "status": agent["status"],
            "questions_answered": agent.get("questions_answered", 0),
            "hints_used": agent.get("hints_used", 0)
        }
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/session/{session_id}/end")
async def end_voice_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End voice interview session and get final report."""
    from backend.database import get_database
    db = get_database()
    
    # Try to end session
    session = await db.interview_sessions.find_one({"session_id": session_id})
    
    if session:
        # Generate final report
        report = await interview_orchestrator.generate_final_report(session_id)
        
        # Generate TTS for farewell
        farewell = f"Thank you for completing the interview. Your overall score is {report['overall_score']} out of 100."
        audio_url = await text_to_speech(farewell)
        
        return {
            "status": "completed",
            "interviewer_state": "asking",
            "audio_url": audio_url,
            "message": farewell,
            "report": report
        }
    
    # Check agent
    agent = await db.agent_interviews.find_one({"session_id": session_id})
    
    if agent:
        from backend.routes.agent_routes import end_agent_interview_logic
        result = await end_agent_interview_logic(session_id)
        
        farewell = f"Interview completed. Your final score is {result['final_score']}. {result['career_coaching'][:100]}"
        audio_url = await text_to_speech(farewell)
        
        return {
            "status": "completed",
            "interviewer_state": "asking",
            "audio_url": audio_url,
            "message": farewell,
            "report": result
        }
    
    raise HTTPException(status_code=404, detail="Session not found")
