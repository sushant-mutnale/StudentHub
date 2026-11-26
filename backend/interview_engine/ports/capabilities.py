from typing import List, Optional, Protocol

from pydantic import BaseModel, Field

from ..contracts.blueprint import BlueprintSlot
from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput


class AnalysisRequest(BaseModel):
    session_id: str
    turn_id: str
    question_id: str
    slot_id: str
    competency: str
    text: str


class QuestionRequest(BaseModel):
    session_id: str
    slot: BlueprintSlot
    purpose: str
    role: Optional[str] = None
    company: Optional[str] = None
    prior_questions: List[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    text: str
    source: str = "generated"


class CompetencyEvaluationInput(BaseModel):
    competency: str
    level: str
    confidence: str
    instances: int
    limitations: List[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    session_id: str
    report_id: str
    role: Optional[str] = None
    company: Optional[str] = None
    competencies: List[CompetencyEvaluationInput] = Field(default_factory=list)


class Analyzer(Protocol):
    async def analyze(self, request: AnalysisRequest) -> Analysis:
        ...


class QuestionGenerator(Protocol):
    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        ...


class Evaluator(Protocol):
    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        ...


class LeasePort(Protocol):
    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        ...

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        ...

    async def takeover(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        ...

    async def release(self, session_id: str, token: str) -> None:
        ...


class Clock(Protocol):
    def now(self):
        ...


class IdGenerator(Protocol):
    def new_id(self) -> str:
        ...

    def new_token(self) -> str:
        ...


class QuestionGeneratorFallback(Exception):
    pass
