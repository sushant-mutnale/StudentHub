from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    timezone: str = "UTC"


class LocationInfo(BaseModel):
    type: str = Field(pattern="^(online|onsite)$")
    url: Optional[str] = None
    address: Optional[str] = None


class InterviewCreateRequest(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    thread_id: Optional[str] = None
    proposed_times: List[TimeSlot]
    location: LocationInfo
    description: Optional[str] = None


class InterviewSummary(BaseModel):
    id: str
    candidate_id: str
    recruiter_id: str
    job_id: Optional[str] = None
    status: str
    scheduled_slot: Optional[TimeSlot] = None
    proposed_times: List[TimeSlot] = []
    location: Optional[LocationInfo] = None
    description: Optional[str] = None
    thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InterviewListResponse(BaseModel):
    interviews: List[InterviewSummary]


class InterviewAcceptRequest(BaseModel):
    slot_index: Optional[int] = None
    selected_slot: Optional[TimeSlot] = None


class InterviewDeclineRequest(BaseModel):
    reason: Optional[str] = None


class InterviewRescheduleRequest(BaseModel):
    proposed_times: List[TimeSlot]
    note: Optional[str] = None


class InterviewCancelRequest(BaseModel):
    reason: Optional[str] = None


class InterviewFeedbackRequest(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None



