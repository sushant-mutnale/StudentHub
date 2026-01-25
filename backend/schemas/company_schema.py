"""
Company Interview Schema
Pydantic models for company interview knowledge API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Data Models ============

class InterviewRound(BaseModel):
    """Single interview round."""
    round: int
    type: str  # online_assessment, phone_screen, onsite, take_home
    name: str
    duration: int  # minutes
    description: str = ""


class CompanyInterviewPattern(BaseModel):
    """Complete interview pattern for a company."""
    company: str
    roles: List[str] = Field(default_factory=list)
    rounds: List[InterviewRound] = Field(default_factory=list)
    total_rounds: int = 0
    dsa_topics: List[str] = Field(default_factory=list)
    behavioral_themes: List[str] = Field(default_factory=list)
    system_design_topics: List[str] = Field(default_factory=list)
    difficulty: str = "medium"
    tips: List[str] = Field(default_factory=list)
    example_questions: List[str] = Field(default_factory=list)
    preparation_time_weeks: int = 4
    sources: List[str] = Field(default_factory=list)
    source: str = "seed_data"  # seed_data, database, default


# ============ API Request/Response Models ============

class CompanyLookupResponse(BaseModel):
    """Response for company lookup."""
    status: str = "success"
    company: str
    role: str = "Software Engineer"
    difficulty: str
    difficulty_score: int  # 1-5
    total_rounds: int
    total_interview_time_minutes: int
    rounds: List[Dict[str, Any]]
    dsa_topics: List[str]
    behavioral_themes: List[str]
    system_design_topics: List[str]
    tips: List[str]
    example_questions: List[str]
    recommended_prep_weeks: int
    data_source: str


class CompanyListItem(BaseModel):
    """Company in list view."""
    company: str
    difficulty: str
    total_rounds: int
    source: str


class CompanyListResponse(BaseModel):
    """Response for listing companies."""
    status: str = "success"
    companies: List[CompanyListItem]
    total: int


class CompanySearchResponse(BaseModel):
    """Response for company search."""
    status: str = "success"
    query: str
    results: List[CompanyListItem]
    total: int


class AddCompanyRequest(BaseModel):
    """Request to add company knowledge."""
    company: str
    company_aliases: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    rounds: List[Dict[str, Any]] = Field(default_factory=list)
    dsa_topics: List[str] = Field(default_factory=list)
    behavioral_themes: List[str] = Field(default_factory=list)
    system_design_topics: List[str] = Field(default_factory=list)
    difficulty: str = "medium"
    tips: List[str] = Field(default_factory=list)
    example_questions: List[str] = Field(default_factory=list)
    preparation_time_weeks: int = 4
    sources: List[str] = Field(default_factory=list)


class AddCompanyResponse(BaseModel):
    """Response after adding company."""
    status: str = "success"
    company: str
    message: str


class PrepTipsRequest(BaseModel):
    """Request for personalized prep tips."""
    company: str
    role: Optional[str] = None
    student_skills: List[str] = Field(default_factory=list)


class PrepTipsResponse(BaseModel):
    """Response with preparation tips."""
    status: str = "success"
    company: str
    tips: List[str]
    dsa_focus: List[str]
    behavioral_focus: List[str]


class DSATopicsResponse(BaseModel):
    """Response with DSA topics."""
    status: str = "success"
    company: str
    topics: List[str]


class BehavioralThemesResponse(BaseModel):
    """Response with behavioral themes."""
    status: str = "success"
    company: str
    themes: List[str]
