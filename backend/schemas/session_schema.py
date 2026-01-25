"""
Interview Session Schema
Pydantic models for interview session management API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RoundType(str, Enum):
    DSA = "dsa"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    HR = "hr"
    TECHNICAL = "technical"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ============ Session Models ============

class RoundPreview(BaseModel):
    """Preview of a round."""
    name: str
    type: str


class InterviewRound(BaseModel):
    """Full round data."""
    round_num: int
    type: str
    name: str
    duration_minutes: int = 60
    questions_answered: int = 0
    score: float = 0
    status: str = "pending"


# ============ API Request Models ============

class StartSessionRequest(BaseModel):
    """Request to start a new interview session."""
    company: str = Field(..., description="Company name, e.g., Amazon, Google")
    role: str = Field(default="Software Engineer", description="Role, e.g., SDE-2, L4")
    resume_id: Optional[str] = None
    jd_text: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer."""
    question_id: str
    answer: str = Field(..., min_length=10)
    code: Optional[str] = None
    time_taken_seconds: int = Field(..., ge=0)


# ============ API Response Models ============

class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    status: str = "success"
    session_id: str
    company: str
    role: str
    total_rounds: int
    rounds_preview: List[RoundPreview]
    estimated_duration_minutes: int
    message: str = "Session created. Call /start to begin."


class StartSessionResponse(BaseModel):
    """Response after starting a session."""
    status: str = "success"
    session_id: str
    current_round: str
    first_question: Dict[str, Any]
    message: str = "Interview started. Good luck!"


class QuestionResponse(BaseModel):
    """Response with a question."""
    question_id: str
    round: str
    round_num: int
    question_type: str
    difficulty: str
    question: str
    hints: List[str] = Field(default_factory=list)
    time_limit_seconds: int = 1800
    questions_in_round: int = 0
    interview_completed: bool = False


class Evaluation(BaseModel):
    """Answer evaluation result."""
    score: int
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class NextAction(BaseModel):
    """Next action decision."""
    action: str  # next_question, next_round, interview_completed
    message: str
    next_round: Optional[str] = None
    next_round_type: Optional[str] = None
    questions_remaining: Optional[int] = None


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer."""
    status: str = "success"
    evaluation: Evaluation
    next_action: NextAction
    new_difficulty: str


class SessionStatusResponse(BaseModel):
    """Response with session status."""
    status: str = "success"
    session_id: str
    session_status: str
    company: str
    role: str
    current_round: int
    total_rounds: int
    total_questions_answered: int
    overall_score: float
    rounds: List[InterviewRound]


class QAItem(BaseModel):
    """Question-answer pair for report."""
    question: str
    question_type: str
    difficulty: str
    answer: str
    code: Optional[str] = None
    score: int
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    time_taken: int


class RoundBreakdown(BaseModel):
    """Round breakdown for report."""
    round_name: str
    round_type: str
    questions_answered: int
    score: float
    status: str


class InterviewReportResponse(BaseModel):
    """Full interview report."""
    status: str = "success"
    session_id: str
    company: str
    role: str
    overall_score: float
    total_questions: int
    total_time_minutes: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    round_breakdown: List[RoundBreakdown]
    questions_and_answers: List[QAItem]
    strengths: List[str]
    areas_to_improve: List[str]
    recommendations: List[str]


class SessionListItem(BaseModel):
    """Session in list view."""
    session_id: str
    company: str
    role: str
    status: str
    overall_score: float
    total_rounds: int
    created_at: datetime


class MySessionsResponse(BaseModel):
    """Response for listing user's sessions."""
    status: str = "success"
    sessions: List[SessionListItem]
    total: int
