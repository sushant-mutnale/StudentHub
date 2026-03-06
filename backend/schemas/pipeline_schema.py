"""
Pipeline Schemas - Pydantic models for pipeline API requests/responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Stage schemas
class StagePermissions(BaseModel):
    can_move_to: List[str] = []
    can_reject: bool = True
    requires_scorecard: bool = False


class PipelineStage(BaseModel):
    id: str
    name: str
    order: int
    type: str  # applied, screening, interview, offer, hired, rejected, withdrawn
    color: str = "#3b82f6"
    auto_trigger: Optional[str] = None
    requires_scorecard: bool = False
    student_visible_name: Optional[str] = None


class PipelineTransition(BaseModel):
    from_stage_id: str
    to_stage_id: str
    allowed_by: List[str] = ["recruiter", "admin"]


# Request schemas
class PipelineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    stages: List[Dict[str, Any]]
    transitions: Optional[List[Dict[str, Any]]] = None


class PipelineUpdateRequest(BaseModel):
    name: Optional[str] = None
    stages: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Dict[str, Any]]] = None


# Response schemas
class PipelineStageResponse(BaseModel):
    id: str
    name: str
    order: int
    type: str
    color: str
    auto_trigger: Optional[str] = None
    requires_scorecard: bool = False
    student_visible_name: Optional[str] = None


class PipelineResponse(BaseModel):
    id: str
    company_id: str
    name: str
    version: int
    active: bool
    is_default: bool = False
    stages: List[PipelineStageResponse]
    transitions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class PipelineListResponse(BaseModel):
    pipelines: List[PipelineResponse]
    total: int


# Pipeline board views
class PipelineBoardCandidate(BaseModel):
    application_id: str
    student_id: str
    student_name: str
    student_avatar: Optional[str] = None
    applied_at: datetime
    last_activity: Optional[datetime] = None
    overall_score: Optional[float] = None
    tags: List[str] = []


class PipelineBoardColumn(BaseModel):
    stage_id: str
    stage_name: str
    stage_type: str
    color: str
    order: int
    candidates: List[PipelineBoardCandidate]
    count: int


class PipelineBoardResponse(BaseModel):
    job_id: str
    job_title: str
    pipeline_id: str
    pipeline_name: str
    columns: List[PipelineBoardColumn]
    total_candidates: int
