from typing import Optional, Sequence

from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput
from ..ports.capabilities import (
    AnalysisRequest,
    EvaluationRequest,
    GeneratedQuestion,
    QuestionRequest,
)

_LIMITATION = "Answer was too brief to demonstrate the competency."


class HeuristicAnalyzer:
    async def analyze(self, request: AnalysisRequest) -> Analysis:
        words = request.text.split()
        if len(words) < 8:
            return Analysis(
                signal="incomplete",
                instance="new",
                substantively_deficient=True,
                limitation=_LIMITATION,
            )
        return Analysis(signal="sufficient", instance="new")


class ScriptedAnalyzer:
    def __init__(self, script: Optional[Sequence[Analysis]] = None):
        self._script = list(script or [])
        self._index = 0
        self._fallback = HeuristicAnalyzer()

    async def analyze(self, request: AnalysisRequest) -> Analysis:
        if self._index < len(self._script):
            analysis = self._script[self._index]
            self._index += 1
            return analysis
        return await self._fallback.analyze(request)


class ScriptedQuestionGenerator:
    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        if request.purpose == "follow_up":
            return GeneratedQuestion(text=request.slot.follow_up_question, source="fallback")
        return GeneratedQuestion(text=request.slot.fallback_question, source="fallback")


class DeterministicEvaluator:
    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        reasons = {}
        parts = []
        for competency in request.competencies:
            label = competency.competency.replace("_", " ")
            reasons[competency.competency] = [
                f"Evidence from {competency.instances} independent answer(s) supports a {competency.level} level.",
                f"Confidence is {competency.confidence} under the published rule.",
            ]
            parts.append(f"{label}: {competency.level} ({competency.confidence} confidence).")
        narrative = " ".join(parts) or "No competency evidence was recorded."
        return EvaluatorOutput(reasons=reasons, narrative=narrative)
