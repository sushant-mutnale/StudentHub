from typing import Dict, List

from pydantic import BaseModel, Field


class Excerpt(BaseModel):
    turn_id: str
    question_id: str
    text: str


class Limitation(BaseModel):
    category: str
    detail: str


class CompetencyReport(BaseModel):
    competency: str
    level: str
    confidence: str
    instance_count: int
    reasons: List[str] = Field(default_factory=list)
    excerpts: List[Excerpt] = Field(default_factory=list)
    limitations: List[Limitation] = Field(default_factory=list)


class ReportBody(BaseModel):
    report_id: str
    session_id: str
    interview_type: str
    mode: str
    target_role: str = ""
    company: str = ""
    duration_seconds: int = 0
    competencies: List[CompetencyReport] = Field(default_factory=list)
    narrative: str = ""
    limitations: List[Limitation] = Field(default_factory=list)
    integrity: Dict[str, object] = Field(default_factory=dict)
    disclosure: Dict[str, object] = Field(default_factory=dict)


class EvaluatorOutput(BaseModel):
    reasons: Dict[str, List[str]] = Field(default_factory=dict)
    narrative: str = ""
