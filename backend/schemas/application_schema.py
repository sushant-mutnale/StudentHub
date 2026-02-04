"""
Application Schemas - Pydantic models for application tracking API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Stage history entry
class StageHistoryEntry(BaseModel):
    stage_id: Optional[str]
    stage_name: str
    changed_by: str
    timestamp: datetime
    reason: Optional[str] = None


# Note schema
class ApplicationNote(BaseModel):
    id: str
    author_id: str
    author_name: str
    content: str
    is_private: bool = True
    created_at: datetime


# Request schemas
class StageMoveRequest(BaseModel):
    new_stage_id: str = Field(..., description="Target stage ID")
    reason: str = Field("", max_length=500)
    student_visible_stage: Optional[str] = None


class AddNoteRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    is_private: bool = True


class AddTagsRequest(BaseModel):
    tags: List[str] = Field(..., min_items=1)


class WithdrawRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# Response schemas
class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    job_title: Optional[str] = None
    company_id: str
    company_name: Optional[str] = None
    student_id: str
    student_name: Optional[str] = None
    current_stage_id: str
    current_stage_name: str
    student_visible_stage: str
    status: str  # active, withdrawn, hired, rejected
    stage_history: List[StageHistoryEntry]
    interview_count: int = 0
    has_offer: bool = False
    tags: List[str] = []
    notes: List[ApplicationNote] = []
    overall_score: Optional[float] = None
    applied_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]
    total: int


class StudentApplicationResponse(BaseModel):
    """What students see about their own application."""
    id: str
    job_id: str
    job_title: str
    company_name: str
    current_stage: str  # student_visible_stage
    status: str
    applied_at: datetime
    last_updated: datetime
    interview_count: int = 0
    has_offer: bool = False


class StudentApplicationsListResponse(BaseModel):
    applications: List[StudentApplicationResponse]
    total: int


# Timeline/Activity feed
class TimelineEvent(BaseModel):
    id: str
    event_type: str  # stage_change, interview, offer, message, scorecard
    title: str
    description: Optional[str] = None
    actor_name: Optional[str] = None
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class ApplicationTimelineResponse(BaseModel):
    application_id: str
    job_title: str
    company_name: str
    events: List[TimelineEvent]
