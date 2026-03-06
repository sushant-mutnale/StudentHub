"""
Scorecard Schemas - Pydantic models for scorecard API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Criteria schema
class ScorecardCriterion(BaseModel):
    name: str
    description: Optional[str] = None
    weight: int = Field(default=1, ge=1, le=100)
    scale_min: int = Field(default=1)
    scale_max: int = Field(default=5)
    required: bool = True


# Template request/response
class ScorecardTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    stage_type: str  # screening, interview
    interview_type: Optional[str] = None  # technical_dsa, system_design, behavioral
    criteria: List[ScorecardCriterion]
    pass_threshold: float = Field(default=3.5, ge=1.0, le=5.0)


class ScorecardTemplateResponse(BaseModel):
    id: str
    company_id: str
    name: str
    stage_type: str
    interview_type: Optional[str] = None
    criteria: List[Dict[str, Any]]
    pass_threshold: float
    is_default: bool = False
    created_at: datetime


class ScorecardTemplateListResponse(BaseModel):
    templates: List[ScorecardTemplateResponse]
    total: int


# Score entry for submission
class ScoreEntry(BaseModel):
    criterion: str
    score: int = Field(..., ge=1, le=5)
    notes: Optional[str] = None


# Scorecard submission
class ScorecardSubmitRequest(BaseModel):
    template_id: str
    stage_id: str
    interview_id: Optional[str] = None
    scores: List[ScoreEntry]
    decision: str = Field(..., pattern="^(pass|hold|reject)$")
    overall_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ScorecardResponse(BaseModel):
    id: str
    application_id: str
    stage_id: str
    interview_id: Optional[str] = None
    template_id: str
    template_name: Optional[str] = None
    evaluator_id: str
    evaluator_name: Optional[str] = None
    scores: List[Dict[str, Any]]
    overall_score: float
    decision: str
    overall_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    submitted_at: datetime


class ScorecardListResponse(BaseModel):
    scorecards: List[ScorecardResponse]
    total: int


# Aggregation
class ScorecardAggregation(BaseModel):
    count: int
    average_score: Optional[float] = None
    decisions: Dict[str, int]
    pass_rate: Optional[float] = None
