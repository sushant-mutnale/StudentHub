from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class OfferCreateRequest(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    thread_id: Optional[str] = None
    package: Dict[str, Any]
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class OfferSummary(BaseModel):
    id: str
    candidate_id: str
    recruiter_id: str
    job_id: Optional[str] = None
    package: Dict[str, Any]
    expires_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OfferListResponse(BaseModel):
    offers: List[OfferSummary]


class OfferUpdateRequest(BaseModel):
    package: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(sent|withdrawn)$")


