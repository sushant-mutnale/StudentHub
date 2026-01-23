from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

from .base import MongoModel


class JobCreate(MongoModel):
    title: str
    description: str
    skills_required: List[str]
    location: str
    # Controls which students can see this job in their feed.
    # For now we support "public" and "students" (treated equivalently in filters),
    # but this leaves room for future targeted visibility modes.
    visibility: Literal["public", "students"] = "public"


class JobResponse(BaseModel):
    """Public job response model with string IDs (Pydantic v2 compatible)."""

    id: str
    recruiter_id: str
    title: str
    description: str
    skills_required: List[str]
    location: str
    created_at: datetime
    visibility: str
    company_name: Optional[str] = None

    class Config:
        from_attributes = True


class JobApplicationCreate(MongoModel):
    """Payload for a student applying to a job."""

    message: str
    resume_url: Optional[str] = None


class JobApplicationResponse(BaseModel):
    """Public job-application response model with string IDs."""

    id: str
    job_id: str
    student_id: str
    student_name: Optional[str] = None
    student_username: Optional[str] = None
    message: str
    resume_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


