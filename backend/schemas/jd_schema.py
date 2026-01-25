"""
Job Description Schema
Pydantic models for JD parsing API requests/responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Parsed Data Models ============

class SalaryRange(BaseModel):
    """Salary range extracted from JD."""
    min: Optional[int] = None
    max: Optional[int] = None
    currency: str = "USD"
    period: str = "yearly"


class JobLocation(BaseModel):
    """Job location details."""
    city: Optional[str] = None
    country: Optional[str] = None
    remote: bool = False
    hybrid: bool = False


class ParsedJobDescription(BaseModel):
    """Complete parsed JD data."""
    job_title: str = ""
    company: str = ""
    required_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    experience_level: str = "not_specified"
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    salary_range: Optional[SalaryRange] = None
    location: Optional[JobLocation] = None
    parsing_confidence: float = 0.0
    ai_enhanced: bool = False


# ============ API Request/Response Models ============

class ParseJDRequest(BaseModel):
    """Request to parse a job description."""
    jd_text: str = Field(..., min_length=50, description="Job description text to parse")
    use_ai_enhancement: bool = Field(False, description="Use AI for better extraction")


class ParseJDResponse(BaseModel):
    """Response after parsing a JD."""
    status: str = "success"
    parsed_data: ParsedJobDescription
    parsing_confidence: float
    ai_enhanced: bool
    message: str = "Job description parsed successfully"


class SaveJDRequest(BaseModel):
    """Request to save a parsed JD."""
    jd_text: str = Field(..., min_length=50)
    parsed_data: Optional[ParsedJobDescription] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


class SavedJD(BaseModel):
    """A saved job description."""
    id: str
    student_id: str
    job_title: str
    company: str
    required_skills: List[str]
    experience_level: str
    parsing_confidence: float
    job_url: Optional[str] = None
    saved_at: datetime


class SaveJDResponse(BaseModel):
    """Response after saving a JD."""
    status: str = "success"
    jd_id: str
    message: str = "Job description saved successfully"


class MyJDsResponse(BaseModel):
    """Response for listing user's saved JDs."""
    status: str = "success"
    job_descriptions: List[SavedJD]
    total: int


class JDDetailResponse(BaseModel):
    """Detailed JD response."""
    status: str = "success"
    id: str
    jd_text: str
    parsed_data: ParsedJobDescription
    job_url: Optional[str] = None
    notes: Optional[str] = None
    saved_at: datetime


class SkillMatchRequest(BaseModel):
    """Request to match skills between resume and JD."""
    resume_id: str
    jd_id: str


class SkillMatchResult(BaseModel):
    """Result of skill matching."""
    matched_skills: List[str]
    missing_required: List[str]
    missing_nice_to_have: List[str]
    match_percentage: float
    recommendation: str


class SkillMatchResponse(BaseModel):
    """Response for skill matching."""
    status: str = "success"
    result: SkillMatchResult


class DeleteJDResponse(BaseModel):
    """Response after deleting a JD."""
    status: str = "success"
    message: str = "Job description deleted successfully"
