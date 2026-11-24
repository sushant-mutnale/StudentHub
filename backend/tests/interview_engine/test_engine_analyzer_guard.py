import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand, SubmitTurnCommand


class RaisingAnalyzer:
    async def analyze(self, request):
        raise RuntimeError("provider exploded")


def _engine():
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=RaisingAnalyzer(),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    return engine, store


async def _started(engine):
    return await engine.start(
        StartSessionCommand(
            candidate_id="c1",
            interview_type="behavioral",
            mode="practice",
            device_id="d1",
            client_request_id="req-guard",
            role="Senior Engineer",
            company="Acme",
        )
    )


async def test_submit_turn_survives_a_raising_analyzer():
    engine, store = _engine()
    started = await _started(engine)
    result = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-guard",
            kind="answer",
            text="I led the migration and cut errors by half.",
            question_id=started.question_id,
        )
    )
    assert result.session_id == started.session_id
    turns = await store.turns_for_session(started.session_id)
    assert len(turns) == 1
    evidence = await store.evidence_for_session(started.session_id)
    assert evidence == []


async def test_second_turn_still_works_after_a_degraded_analysis():
    engine, store = _engine()
    started = await _started(engine)
    first = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-a",
            kind="answer",
            text="I led the migration and cut errors by half.",
            question_id=started.question_id,
        )
    )
    second = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-b",
            kind="answer",
            text="I also mentored two engineers through the rollout.",
            question_id=first.question_id,
        )
    )
    assert second.session_id == started.session_id
    assert len(await store.turns_for_session(started.session_id)) == 2


async def test_build_engine_reuses_one_limiter_across_calls():
    from backend.interview_engine.adapters import factory

    factory._llm_adapters_built = False
    factory._llm_adapters = None

    class _Settings:
        groq_llm_enabled = True
        groq_api_key_1 = "gsk_a"
        groq_api_key_2 = None
        groq_api_key_3 = None
        groq_model = "openai/gpt-oss-120b"
        groq_base_url = "https://example.invalid"
        groq_rpm_per_key = 25
        groq_rpd_per_key = 900
        groq_tpm_per_key = 7000
        groq_tpd_per_key = 180000
        groq_max_wait_seconds = 60
        groq_request_timeout_seconds = 30
        groq_reasoning_effort = "low"

        def __getattr__(self, name):
            raise AttributeError(name)

    first = factory._shared_llm_adapters(_Settings())
    second = factory._shared_llm_adapters(_Settings())
    assert first is second
    factory._llm_adapters_built = False
    factory._llm_adapters = None
