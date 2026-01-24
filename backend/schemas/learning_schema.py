"""
Learning Module Pydantic Schemas
Request/Response models for Gap Analysis and Learning Paths
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Gap Analysis Schemas ============

class SkillGap(BaseModel):
    skill: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    current_level: int = 0
    target_level: int = 80
    is_required: bool = True


class GapAnalysisRequest(BaseModel):
    student_id: Optional[str] = None
    student_skills: List[str] = Field(default_factory=list, description="Student's current skills")
    job_id: Optional[str] = None
    job_required_skills: List[str] = Field(..., description="Required skills for the job")
    job_nice_to_have_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")


class GapAnalysisResponse(BaseModel):
    status: str = "success"
    student_id: Optional[str] = None
    job_id: Optional[str] = None
    analyzed_at: str
    student_skills: List[str]
    job_required_skills: List[str]
    job_nice_to_have: List[str]
    gaps: List[SkillGap]
    match_percentage: float
    gap_score: float
    recommendations: str
    high_priority_count: int
    total_gaps: int


# ============ Learning Path Schemas ============

class LearningResource(BaseModel):
    resource_id: str
    type: str  # video, article, course, practice
    title: str
    url: str
    duration_minutes: Optional[int] = None
    source: str
    level: str = "beginner"  # beginner, intermediate, advanced
    completed: bool = False
    completed_at: Optional[datetime] = None


class LearningStage(BaseModel):
    stage_number: int
    stage_name: str  # Foundation, Intermediate, Advanced
    duration_weeks: int
    topics: List[str]
    resources: List[LearningResource]
    assessment: Optional[Dict[str, Any]] = None
    status: str = "not_started"  # not_started, in_progress, completed
    completed_at: Optional[datetime] = None


class LearningPathProgress(BaseModel):
    current_stage: int = 0
    completion_percentage: float = 0.0
    time_spent_minutes: int = 0
    estimated_completion_date: Optional[str] = None


class LearningPath(BaseModel):
    id: Optional[str] = None
    student_id: str
    skill: str
    current_level: int = 0
    target_level: int = 80
    gap_priority: str = "HIGH"
    stages: List[LearningStage]
    progress: LearningPathProgress
    estimated_completion_weeks: int
    ai_advice: str = ""  # AI-generated personalized coaching
    ai_powered: bool = False  # Whether AI was used for personalization
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GeneratePathRequest(BaseModel):
    student_id: str
    gaps: List[SkillGap]


class GeneratePathResponse(BaseModel):
    status: str = "success"
    learning_paths: List[LearningPath]
    total_estimated_weeks: int
    ai_powered_paths: int = 0  # How many paths used AI personalization


class MarkProgressRequest(BaseModel):
    learning_path_id: str
    stage_number: int
    resource_index: int
    action: str = "completed"  # completed, skipped


class MarkProgressResponse(BaseModel):
    status: str = "success"
    learning_path_id: str
    new_completion_percentage: float
    stage_status: str
    message: str


class MyPathsResponse(BaseModel):
    status: str = "success"
    learning_paths: List[LearningPath]
    total_paths: int
    overall_progress: float
