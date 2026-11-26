import hashlib
import uuid
from typing import Optional

from pydantic import BaseModel

from ..contracts.messages import SessionView


class LegacyStartRequest(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    difficulty: Optional[str] = None
    interview_type: str = "behavioral"
    mode: str = "practice"
    device_id: Optional[str] = None
    request_id: Optional[str] = None


class LegacyAnswerRequest(BaseModel):
    session_id: str
    answer: str
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    question_id: Optional[str] = None
    kind: str = "answer"


class LegacyHintRequest(BaseModel):
    session_id: str
    level: int = 1
    device_id: Optional[str] = None


class LegacyEndRequest(BaseModel):
    session_id: str
    device_id: Optional[str] = None
    end_request_id: Optional[str] = None


class LegacyFeedbackRequest(BaseModel):
    session_id: str
    device_id: Optional[str] = None


class LegacyResumeRequest(BaseModel):
    session_id: str
    device_id: Optional[str] = None
    command_id: Optional[str] = None


def answer_idempotency_key(candidate_id: str, session_id: str, request_id: Optional[str], body: str) -> str:
    seed = f"{candidate_id}:{session_id}:{request_id or uuid.uuid4().hex}:{hashlib.sha256(body.encode()).hexdigest()}"
    return hashlib.sha256(seed.encode()).hexdigest()


def end_command_id(candidate_id: str, session_id: str, end_request_id: Optional[str]) -> str:
    seed = f"{candidate_id}:{session_id}:{end_request_id or 'fingerprint'}"
    return hashlib.sha256(seed.encode()).hexdigest()


def to_start_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "question": result.first_question,
        "interviewer_message": result.first_question,
        "status": result.status,
        "request_id": result.client_request_id,
        "question_id": result.question_id,
        "fencing_token": result.fencing_token,
    }


def to_answer_response(result, view: SessionView) -> dict:
    response = {
        "session_id": result.session_id,
        "status": result.status,
        "next_action": result.next_action,
        "next_question": result.question,
        "question_id": result.question_id,
        "question_pending": result.question_pending,
        "turn_request_id": None,
        "questions_answered": view.questions_answered,
        "report_id": result.report_id,
        "report_status": result.report_outcome,
    }
    if result.reply:
        response["reply"] = result.reply
    return response


def to_end_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "status": result.status,
        "report_id": result.report_id,
        "report_status": result.report_outcome,
    }


def to_feedback_response(report, body: Optional[dict]) -> dict:
    return {
        "session_id": report.session_id,
        "report_id": report.report_id,
        "report_status": report.outcome,
        "report": body if report.outcome == "ready" else None,
    }


def to_hint_response(result) -> dict:
    return {
        "hint": result.hint,
        "hints_used": result.hints_used,
        "remaining": result.remaining,
        "question_id": result.question_id,
    }


def to_resume_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "status": result.status,
        "question": result.question,
        "question_id": result.question_id,
        "fencing_token": result.fencing_token,
        "question_pending": result.question_pending,
    }
