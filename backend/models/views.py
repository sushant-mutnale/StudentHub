"""
Read Models (Views) for CQRS

These models are optimized for specific UI views and are updated asynchronously
by event handlers (Projections).
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PipelineBoardCandidateView(BaseModel):
    """Denormalized candidate view for the board."""
    application_id: str
    student_id: str
    student_name: str
    student_avatar: Optional[str] = None
    applied_at: datetime
    last_activity: Optional[datetime] = None
    overall_score: Optional[float] = None
    tags: List[str] = []

class PipelineBoardColumnView(BaseModel):
    """Column in the pipeline board."""
    stage_id: str
    stage_name: str
    stage_type: str
    color: str
    order: int
    candidates: List[PipelineBoardCandidateView] = []
    count: int = 0

class PipelineBoardView(BaseModel):
    """
    Pre-aggregated view of a pipeline board for a specific job.
    Collection: view_pipeline_boards
    """
    id: str  # job_id
    job_id: str
    job_title: str
    pipeline_id: str
    pipeline_name: str
    company_id: str
    columns: List[PipelineBoardColumnView] = []
    total_candidates: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 0  # Optimistic locking / sync tracking
