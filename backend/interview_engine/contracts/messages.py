from typing import List, Optional

from pydantic import BaseModel, Field


class StartSessionCommand(BaseModel):
    candidate_id: str
    interview_type: str = "behavioral"
    mode: str = "practice"
    device_id: str
    client_request_id: str
    role: Optional[str] = None
    company: Optional[str] = None
    job_description: Optional[str] = None
    consent: Optional[dict] = None


class StartSessionResult(BaseModel):
    session_id: str
    status: str
    first_question: str
    question_id: str
    fencing_token: str
    version: int = 0
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    client_request_id: Optional[str] = None


class SubmitTurnCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    turn_idempotency_key: str
    kind: str = "answer"
    text: str = ""
    question_id: Optional[str] = None
    expected_version: Optional[int] = None


class SubmitTurnResult(BaseModel):
    session_id: str
    status: str
    next_action: str
    question: Optional[str] = None
    question_id: Optional[str] = None
    reply: Optional[str] = None
    version: int = 0
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    question_pending: bool = False


class RequestHintCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    hint_idempotency_key: str
    question_id: Optional[str] = None
    expected_version: Optional[int] = None


class HintResult(BaseModel):
    hint: str
    hints_used: int
    remaining: int
    version: int
    question_id: str


class ResumeSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    command_id: Optional[str] = None


class ResumeSessionResult(BaseModel):
    session_id: str
    status: str
    fencing_token: str
    question: Optional[str] = None
    question_id: Optional[str] = None
    version: int = 0
    question_pending: bool = False


class PauseSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    command_id: str
    reason: str = "candidate_paused"
    expected_version: Optional[int] = None


class EndSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    end_command_id: str
    reason: str = "candidate_completed"


class EndSessionResult(BaseModel):
    session_id: str
    status: str
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None


class SessionView(BaseModel):
    session_id: str
    status: str
    version: int
    question_pending: bool
    outstanding_question: Optional[str] = None
    question_id: Optional[str] = None
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    fencing_token: Optional[str] = None
    hints_used: int = 0
    hints_remaining: int = 0
    plan_position: int = 0
    current_slot_id: Optional[str] = None
    questions_answered: int = 0
