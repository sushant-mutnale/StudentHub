import os

import pytest

from backend.interview_engine.adapters.llm import (
    GroqAnalyzer,
    GroqEvaluator,
    GroqQuestionGenerator,
)
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import (
    EndSessionCommand,
    RequestHintCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from backend.services.llm.groq import GroqLLMClient
from backend.services.llm.keys import ApiKeyPool
from backend.services.llm.limiter import Budgets, InMemoryRateLimiter


def _keys():
    return [
        key
        for key in (
            os.environ.get("GROQ_API_KEY_1"),
            os.environ.get("GROQ_API_KEY_2"),
            os.environ.get("GROQ_API_KEY_3"),
        )
        if key
    ]


def _client():
    budgets = Budgets(rpm=25, rpd=900, tpm=7000, tpd=180000)
    return GroqLLMClient(
        ApiKeyPool(_keys()),
        InMemoryRateLimiter(budgets),
        model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        request_timeout_seconds=30,
        max_wait_seconds=60,
        reasoning_effort=os.environ.get("GROQ_REASONING_EFFORT", "low"),
        max_attempts=3,
    )


@pytest.mark.llm
@pytest.mark.integration
async def test_real_interview_completes_and_produces_a_report():
    keys = _keys()
    if not keys:
        pytest.skip("no GROQ_API_KEY_1/2/3 set")

    client = _client()
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=GroqAnalyzer(client),
        generator=GroqQuestionGenerator(client),
        evaluator=GroqEvaluator(client),
    )

    started = await engine.start(
        StartSessionCommand(
            candidate_id="c-live",
            interview_type="behavioral",
            mode="practice",
            device_id="d-live",
            client_request_id="live-req-1",
            role="Backend Engineer",
            company="Acme",
        )
    )
    assert started.question_id

    answer = (
        "I owned the checkout migration. I split it into three phases, wrote the "
        "rollback plan, and cut error rates by half within six weeks."
    )
    result = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            turn_idempotency_key="live-turn-1",
            kind="answer",
            text=answer,
            question_id=started.question_id,
        )
    )
    assert result.session_id == started.session_id

    hint = await engine.request_hint(
        RequestHintCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            hint_idempotency_key="live-hint-1",
            question_id=result.question_id,
        )
    )
    assert hint.hint
    assert hint.hints_used == 1
    assert hint.question_id == result.question_id

    ended = await engine.end(
        EndSessionCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            end_command_id="live-end-1",
        )
    )
    assert ended.session_id == started.session_id
    assert ended.status == "completed"

    processed = await engine.drain_outbox(limit=10)
    assert processed == 1

    report = await engine.get_report("c-live", ended.report_id)
    assert report.outcome == "ready"
    assert report.body is not None
    narrative = report.body.get("narrative")
    assert isinstance(narrative, str) and narrative.strip()
    assert isinstance(report.body.get("competencies"), list)
