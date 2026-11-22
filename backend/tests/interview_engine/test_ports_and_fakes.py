from datetime import datetime

import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.contracts.blueprint import BlueprintSlot
from backend.interview_engine.contracts.records import Analysis, SessionRecord


def _record(session_id="s1"):
    return SessionRecord(
        session_id=session_id, candidate_id="c1", interview_type="behavioral", mode="practice",
        status="planned", version=0, event_sequence=0, last_applied_sequence=0,
        fencing_token="t1", device_id="d1",
        blueprint={"groups": []},
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_memory_store_rolls_back_on_error():
    store = InMemorySessionStore()
    record = _record()
    async with store.transaction():
        await store.insert(record)
    with pytest.raises(RuntimeError):
        async with store.transaction():
            loaded = await store.load("s1")
            loaded.status = "completed"
            await store.replace(loaded, expected_version=0)
            raise RuntimeError("boom")
    loaded = await store.load("s1")
    assert loaded.status == "planned"


@pytest.mark.asyncio
async def test_memory_store_optimistic_version_check():
    store = InMemorySessionStore()
    async with store.transaction():
        await store.insert(_record())
    loaded = await store.load("s1")
    loaded.version = 1
    assert await store.replace(loaded, expected_version=0) is True
    assert await store.replace(loaded, expected_version=0) is False


@pytest.mark.asyncio
async def test_scripted_analyzer_yields_script_then_heuristic():
    analyzer = ScriptedAnalyzer([Analysis(signal="sufficient", instance="new")])
    from backend.interview_engine.ports.capabilities import AnalysisRequest

    req = AnalysisRequest(
        session_id="s1", turn_id="t1", question_id="q1", slot_id="s1",
        competency="c", text="short",
    )
    assert (await analyzer.analyze(req)).signal == "sufficient"
    assert (await analyzer.analyze(req)).signal == "incomplete"


@pytest.mark.asyncio
async def test_heuristic_analyzer_is_deterministic():
    analyzer = HeuristicAnalyzer()
    from backend.interview_engine.ports.capabilities import AnalysisRequest

    short = AnalysisRequest(
        session_id="s1", turn_id="t1", question_id="q1", slot_id="s1",
        competency="c", text="too short",
    )
    long = AnalysisRequest(
        session_id="s1", turn_id="t2", question_id="q2", slot_id="s2",
        competency="c",
        text="In my last project I owned the ingestion pipeline and cut latency by half after profiling the bottleneck.",
    )
    assert (await analyzer.analyze(short)).signal == "incomplete"
    assert (await analyzer.analyze(long)).signal == "sufficient"


@pytest.mark.asyncio
async def test_question_generator_uses_follow_up_and_fallback():
    slot = BlueprintSlot(
        slot_id="s1", competency="c", dimension="c", difficulty="intermediate",
        intent="intent", fallback_question="fallback", follow_up_question="follow",
        clarification_text="clarify", hint_text="hint",
    )
    generator = ScriptedQuestionGenerator()
    from backend.interview_engine.ports.capabilities import QuestionRequest

    base = dict(session_id="s1", slot=slot, role="Engineer", company="Acme", prior_questions=[])
    first = await generator.generate(QuestionRequest(purpose="first_question", **base))
    follow = await generator.generate(QuestionRequest(purpose="follow_up", **base))
    assert first.text == "fallback"
    assert follow.text == "follow"


@pytest.mark.asyncio
async def test_deterministic_evaluator_produces_reasons():
    evaluator = DeterministicEvaluator()
    from backend.interview_engine.ports.capabilities import (
        CompetencyEvaluationInput,
        EvaluationRequest,
    )

    output = await evaluator.evaluate(
        EvaluationRequest(
            session_id="s1", report_id="r1", role="Engineer", company="Acme",
            competencies=[CompetencyEvaluationInput(
                competency="problem_solving", level="proficient", confidence="medium",
                instances=2, limitations=[],
            )],
        )
    )
    assert "problem_solving" in output.reasons
    assert output.narrative


@pytest.mark.asyncio
async def test_in_memory_lease_conflicts_and_takeover():
    lease = InMemoryLease()
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    assert await lease.confirm("s1", "d1", "t1") is True
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.acquire("s1", "d2", "t2", 60) is False
    assert await lease.takeover("s1", "d2", "t2", 60) is True
    assert await lease.confirm("s1", "d2", "t2") is True
    assert await lease.confirm("s1", "d1", "t1") is False


def test_system_adapters():
    clock = SystemClock()
    ids = UuidIds()
    assert isinstance(clock.now(), datetime)
    assert ids.new_id() != ids.new_id()
    assert len(ids.new_token()) >= 16
