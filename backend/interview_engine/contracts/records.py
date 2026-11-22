from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .blueprint import Blueprint


class ConsentSnapshot(BaseModel):
    evaluation: bool = True
    memory: bool = False
    model_improvement: bool = False


class SessionRecord(BaseModel):
    session_id: str
    candidate_id: str
    interview_type: str
    mode: str
    status: str
    version: int
    event_sequence: int
    last_applied_sequence: int
    fencing_token: str
    device_id: str
    blueprint: Blueprint
    client_request_id: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    plan_position: int = 0
    current_slot_id: Optional[str] = None
    current_question_id: Optional[str] = None
    outstanding_question: Optional[str] = None
    question_pending: bool = True
    pending_question_request: Optional[Dict[str, Any]] = None
    follow_up_used: Dict[str, int] = Field(default_factory=dict)
    hint_count: int = 0
    hint_budget: int = 2
    pause_count: int = 0
    pause_started_at: Optional[datetime] = None
    total_pause_seconds: int = 0
    disconnect_count: int = 0
    consent: ConsentSnapshot = Field(default_factory=ConsentSnapshot)
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TurnRecord(BaseModel):
    turn_id: str
    session_id: str
    sequence: int
    kind: str
    question_id: str
    slot_id: str
    text: str
    reply: Optional[str] = None
    idempotency_key: str
    device_id: str
    created_at: datetime


class Analysis(BaseModel):
    signal: str
    instance: str
    contradiction: bool = False
    substantively_deficient: bool = False
    limitation: Optional[str] = None


class EvidenceRecord(BaseModel):
    evidence_id: str
    session_id: str
    turn_id: str
    question_id: str
    slot_id: str
    competency: str
    signal: str
    instance: str
    contradiction: bool = False
    difficulty: str
    adapted: bool = False
    created_at: datetime


class QuestionRecord(BaseModel):
    question_id: str
    session_id: str
    slot_id: str
    question_generation_key: str
    purpose: str
    text: str
    source: str
    created_at: datetime


class HintRecord(BaseModel):
    hint_id: str
    session_id: str
    hint_idempotency_key: str
    question_id: str
    text: str
    hints_used: int = 1
    created_at: datetime


class TurnCommandRecord(BaseModel):
    session_id: str
    idempotency_key: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ReportRecord(BaseModel):
    report_id: str
    session_id: str
    outcome: str
    body: Optional[Dict[str, Any]] = None
    attempts: int = 0
    created_at: datetime
    updated_at: datetime


class EventRecord(BaseModel):
    event_id: str
    session_id: str
    event_sequence: int
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class OutboxRecord(BaseModel):
    outbox_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    worker_id: Optional[str] = None
    created_at: datetime
