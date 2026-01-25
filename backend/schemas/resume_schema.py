"""
Resume Schema
Pydantic models for resume parsing API requests/responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Parsed Data Models ============

class ParsedContact(BaseModel):
    """Contact information extracted from resume."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None


class ParsedExperience(BaseModel):
    """Work experience entry."""
    company: str = ""
    title: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: str = ""


class ParsedEducation(BaseModel):
    """Education entry."""
    degree: str = ""
    institution: str = ""
    year: Optional[str] = None
    gpa: Optional[str] = None


class ParsedProject(BaseModel):
    """Project entry."""
    name: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    """Complete parsed resume data."""
    contact: ParsedContact = Field(default_factory=ParsedContact)
    skills: List[str] = Field(default_factory=list)
    experience: List[ParsedExperience] = Field(default_factory=list)
    education: List[ParsedEducation] = Field(default_factory=list)
    projects: List[ParsedProject] = Field(default_factory=list)
    parsing_confidence: float = 0.0
    ai_enhanced: bool = False
    extraction_method: str = ""


# ============ API Request/Response Models ============

class ResumeUploadResponse(BaseModel):
    """Response after uploading a resume."""
    status: str = "success"
    resume_id: str
    file_name: str
    parsed_data: ParsedResume
    parsing_confidence: float
    ai_enhanced: bool
    message: str = "Resume parsed successfully"


class ResumeListItem(BaseModel):
    """Resume item in list view."""
    id: str
    file_name: str
    name: Optional[str] = None
    parsing_confidence: float
    skills_count: int
    uploaded_at: datetime


class MyResumesResponse(BaseModel):
    """Response for listing user's resumes."""
    status: str = "success"
    resumes: List[ResumeListItem]
    total: int


class ResumeDetailResponse(BaseModel):
    """Detailed resume response."""
    status: str = "success"
    id: str
    file_name: str
    file_url: Optional[str] = None
    parsed_data: ParsedResume
    uploaded_at: datetime
    updated_at: Optional[datetime] = None


class ReparseRequest(BaseModel):
    """Request to reparse a resume with AI enhancement."""
    use_ai: bool = True


class ReparseResponse(BaseModel):
    """Response after reparsing."""
    status: str = "success"
    resume_id: str
    previous_confidence: float
    new_confidence: float
    ai_enhanced: bool
    changes_made: List[str] = Field(default_factory=list)


class DeleteResponse(BaseModel):
    """Response after deleting a resume."""
    status: str = "success"
    message: str = "Resume deleted successfully"
