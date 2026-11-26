import json
import logging
from typing import Optional

from ...services.llm import prompts
from ...services.llm.groq import LLMUnavailable
from ..contracts.enums import InstanceKind, Signal
from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput
from ..ports.capabilities import (
    AnalysisRequest,
    EvaluationRequest,
    GeneratedQuestion,
    QuestionRequest,
)

logger = logging.getLogger(__name__)

_SIGNALS = {member.value for member in Signal}
_INSTANCES = {member.value for member in InstanceKind}
_UNAVAILABLE = "analysis_unavailable"


def _degraded_analysis() -> Analysis:
    return Analysis(
        signal="incomplete",
        instance="same",
        substantively_deficient=True,
        limitation=_UNAVAILABLE,
    )


def _analyzer_user(request: AnalysisRequest) -> str:
    return (
        f"Competency: {request.competency}\n"
        f"Question id: {request.question_id}\n"
        f"Answer:\n{request.text}"
    )


def _generator_user(request: QuestionRequest) -> str:
    prior = "\n".join(f"- {text}" for text in request.prior_questions) or "- none"
    return (
        f"Role: {request.role or 'unspecified'}\n"
        f"Company: {request.company or 'unspecified'}\n"
        f"Competency: {request.slot.competency}\n"
        f"Intent: {request.slot.intent}\n"
        f"Purpose: {request.purpose}\n"
        f"Already asked:\n{prior}"
    )


def _evaluator_user(request: EvaluationRequest) -> str:
    lines = [
        f"- {item.competency}: level={item.level}, confidence={item.confidence}, "
        f"instances={item.instances}, limitations={item.limitations}"
        for item in request.competencies
    ]
    body = "\n".join(lines) or "- none"
    return (
        f"Role: {request.role or 'unspecified'}\n"
        f"Company: {request.company or 'unspecified'}\n"
        f"Competencies:\n{body}"
    )


def _parse_analysis(text: str) -> Analysis:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("analysis must be an object")
    instance = data.get("instance")
    signal = data.get("signal")
    if instance not in _INSTANCES or signal not in _SIGNALS:
        raise ValueError("analysis is out of contract")
    if signal == "off_topic":
        instance = "same"
    limitation = data.get("limitation")
    if limitation is not None and not isinstance(limitation, str):
        raise ValueError("limitation must be a string or null")
    contradiction = data.get("contradiction", False)
    if not isinstance(contradiction, bool):
        raise ValueError("contradiction must be a boolean")
    substantively_deficient = data.get("substantively_deficient", False)
    if not isinstance(substantively_deficient, bool):
        raise ValueError("substantively_deficient must be a boolean")
    return Analysis(
        signal=signal,
        instance=instance,
        contradiction=contradiction,
        substantively_deficient=substantively_deficient,
        limitation=limitation,
    )


def _parse_evaluation(text: str, request: EvaluationRequest) -> EvaluatorOutput:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise LLMUnavailable("malformed_evaluation") from exc
    if not isinstance(data, dict):
        raise LLMUnavailable("malformed_evaluation")
    if set(data) - {"reasons", "narrative"}:
        raise LLMUnavailable("malformed_evaluation")
    raw_reasons = data.get("reasons")
    narrative = data.get("narrative")
    if not isinstance(raw_reasons, dict) or not isinstance(narrative, str):
        raise LLMUnavailable("malformed_evaluation")
    if not narrative.strip():
        raise LLMUnavailable("malformed_evaluation")
    known = {item.competency for item in request.competencies}
    if set(raw_reasons) != known:
        raise LLMUnavailable("malformed_evaluation")
    reasons = {}
    for competency, values in raw_reasons.items():
        if not isinstance(values, list):
            raise LLMUnavailable("malformed_evaluation")
        if not all(isinstance(value, str) for value in values):
            raise LLMUnavailable("malformed_evaluation")
        reasons[competency] = values
    return EvaluatorOutput(reasons=reasons, narrative=narrative)


class GroqAnalyzer:
    def __init__(self, client, max_completion_tokens: int = 600, temperature: float = 0.0):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def analyze(self, request: AnalysisRequest) -> Analysis:
        try:
            completion = await self._client.complete(
                system=prompts.ANALYZER_SYSTEM,
                user=_analyzer_user(request),
                max_completion_tokens=self._max_completion_tokens,
                temperature=self._temperature,
                response_format="json_object",
            )
            return _parse_analysis(completion.text)
        except Exception:
            logger.warning("analyzer unavailable, degrading turn", exc_info=True)
            return _degraded_analysis()


class GroqQuestionGenerator:
    def __init__(self, client, max_completion_tokens: int = 400, temperature: float = 0.5):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        try:
            completion = await self._client.complete(
                system=prompts.GENERATOR_SYSTEM,
                user=_generator_user(request),
                max_completion_tokens=self._max_completion_tokens,
                temperature=self._temperature,
            )
        except Exception:
            logger.warning("question generation unavailable", exc_info=True)
            return GeneratedQuestion(text="", source="fallback")
        text = completion.text.strip()
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1].strip()
        if not text:
            return GeneratedQuestion(text="", source="fallback")
        return GeneratedQuestion(text=text, source="generated")


class GroqEvaluator:
    def __init__(self, client, max_completion_tokens: int = 1200, temperature: float = 0.0):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        completion = await self._client.complete(
            system=prompts.EVALUATOR_SYSTEM,
            user=_evaluator_user(request),
            max_completion_tokens=self._max_completion_tokens,
            temperature=self._temperature,
            response_format="json_object",
        )
        return _parse_evaluation(completion.text, request)


class LLMAdapters:
    def __init__(self, analyzer, generator, evaluator):
        self.analyzer = analyzer
        self.generator = generator
        self.evaluator = evaluator


def build_llm_adapters(settings, limiter=None, client=None) -> Optional[LLMAdapters]:
    keys = [
        key
        for key in (
            settings.groq_api_key_1,
            settings.groq_api_key_2,
            settings.groq_api_key_3,
        )
        if key
    ]
    if not settings.groq_llm_enabled or not keys:
        return None

    if client is None:
        from ...redis_client import get_redis
        from ...services.llm.groq import GroqLLMClient
        from ...services.llm.keys import ApiKeyPool
        from ...services.llm.limiter import Budgets, InMemoryRateLimiter
        from ...services.llm.redis_limiter import FallbackRateLimiter, RedisRateLimiter

        budgets = Budgets(
            rpm=settings.groq_rpm_per_key,
            rpd=settings.groq_rpd_per_key,
            tpm=settings.groq_tpm_per_key,
            tpd=settings.groq_tpd_per_key,
        )
        if limiter is None:
            limiter = FallbackRateLimiter(
                RedisRateLimiter(get_redis(), budgets),
                InMemoryRateLimiter(budgets),
            )
        client = GroqLLMClient(
            ApiKeyPool(keys),
            limiter,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            request_timeout_seconds=settings.groq_request_timeout_seconds,
            max_wait_seconds=settings.groq_max_wait_seconds,
            reasoning_effort=settings.groq_reasoning_effort,
        )

    return LLMAdapters(
        GroqAnalyzer(client),
        GroqQuestionGenerator(client),
        GroqEvaluator(client),
    )
