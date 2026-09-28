from datetime import datetime
from typing import List, Optional, Literal, Any

from pydantic import BaseModel, EmailStr, Field, model_validator

from .base import MongoModel


class SkillSchema(BaseModel):
    name: str
    level: int = 0  # 0-100
    proficiency: str = "Beginner"  # Beginner, Intermediate, Advanced
    confidence: int = 0  # 0-100
    evidence: List[str] = Field(default_factory=list)  # assessment IDs, project links
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_string_or_dict(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"name": data}
        return data

class AIProfileSchema(BaseModel):
    overall_score: float = 0.0
    skill_score: float = 0.0
    learning_score: float = 0.0
    interview_score: float = 0.0
    activity_score: float = 0.0
    profile_completeness: float = 0.0
    last_computed_at: datetime = Field(default_factory=datetime.utcnow)

class UserBase(MongoModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=2000)
    skills: List[SkillSchema] = Field(default_factory=list)
    ai_profile: Optional[AIProfileSchema] = None
    connections: List[str] = Field(default_factory=list)


class StudentCreate(UserBase):
    full_name: str
    password: str = Field(..., min_length=8)
    prn: str
    college: str
    branch: str
    year: str
    role: str = "student"
    otp: Optional[str] = None  # Required for verification


class RecruiterCreate(UserBase):
    password: str = Field(..., min_length=8)
    company_name: str
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None
    role: str = "recruiter"
    otp: Optional[str] = None  # Required for verification


class UserLogin(MongoModel):
    username: str
    password: str
    role: str


class UserPublic(BaseModel):
    """Public user response model with string IDs (Pydantic v2 compatible)."""
    id: str
    role: Literal["student", "recruiter"]
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    prn: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[str] = None
    company_name: Optional[str] = None
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: List[SkillSchema] = Field(default_factory=list)
    ai_profile: Optional[AIProfileSchema] = None
    connections: List[str] = Field(default_factory=list)
    onboarding_completed: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatchExplanation(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    skill_match_score: float
    proficiency_score: float
    activity_score: float
    completeness_score: float
    total_score: float
    # Full authoritative breakdown from the shared ScoringEngine.
    # These fields use the same 6-component model for student and recruiter.
    skill_match: Optional[float] = None
    proficiency_fit: Optional[float] = None
    freshness: Optional[float] = None
    location_match: Optional[float] = None
    career_alignment: Optional[float] = None
    ai_readiness: Optional[float] = None


class MatchResult(UserPublic):
    match_score: float
    explanation: MatchExplanation


class UserUpdate(MongoModel):
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=2000)
    skills: Optional[List[SkillSchema]] = None
    ai_profile: Optional[AIProfileSchema] = None
    connections: Optional[List[str]] = None
    full_name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[str] = None
    prn: Optional[str] = None
    company_name: Optional[str] = None
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None
    onboarding_completed: Optional[bool] = None


