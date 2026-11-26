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
from backend.interview_engine.contracts.records import (
    Analysis,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
)


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
    assert await lease.current("s1") == ("d1", "t1")
    assert await lease.confirm("s1", "d1", "t1") is True
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.acquire("s1", "d2", "t2", 60) is False
    assert (
        await lease.takeover("s1", "d2", "t2", 60, expected_token="t1") is True
    )
    assert await lease.confirm("s1", "d2", "t2") is True
    assert await lease.confirm("s1", "d1", "t1") is False


def test_system_adapters():
    clock = SystemClock()
    ids = UuidIds()
    assert isinstance(clock.now(), datetime)
    assert ids.new_id() != ids.new_id()
    assert len(ids.new_token()) >= 16


@pytest.mark.asyncio
async def test_heuristic_analyzer_degrades_to_incomplete_same():
    from backend.interview_engine.ports.capabilities import AnalysisRequest

    analyzer = HeuristicAnalyzer()
    result = await analyzer.analyze(
        AnalysisRequest(
            session_id="s1", turn_id="t1", question_id="q1", slot_id="s1",
            competency="c", text="too short",
        )
    )
    assert result.signal == "incomplete"
    assert result.instance == "same"
    assert result.substantively_deficient is True
    assert result.limitation


def _outbox(outbox_id="o1"):
    return OutboxRecord(
        outbox_id=outbox_id,
        event_type="session.completed",
        payload={"session_id": "s1"},
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_outbox_claim_process_and_fail_cycle():
    store = InMemorySessionStore()
    async with store.transaction():
        await store.append_outbox(_outbox())

    claimed = await store.claim_outbox("w1", 10)
    assert len(claimed) == 1
    assert claimed[0].status == "processing"
    assert claimed[0].attempts == 1
    assert claimed[0].worker_id == "w1"

    assert await store.claim_outbox("w2", 10) == []

    await store.mark_outbox_failed("o1", "boom")
    assert store.outbox_errors["o1"] == "boom"
    reclaimed = await store.claim_outbox("w2", 10)
    assert len(reclaimed) == 1
    assert reclaimed[0].attempts == 2
    assert reclaimed[0].worker_id == "w2"

    await store.mark_outbox_processed("o1")
    assert await store.claim_outbox("w3", 10) == []


@pytest.mark.asyncio
async def test_outbox_rolls_back_with_transaction():
    store = InMemorySessionStore()
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.append_outbox(_outbox())
            raise RuntimeError("boom")
    assert await store.claim_outbox("w1", 10) == []


@pytest.mark.asyncio
async def test_nested_transaction_rolls_back_inner_only():
    store = InMemorySessionStore()
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.insert(_record())
            with pytest.raises(RuntimeError):
                async with store.transaction():
                    loaded = await store.load("s1")
                    loaded.status = "completed"
                    await store.replace(loaded, expected_version=0)
                    raise RuntimeError("inner")
            raise RuntimeError("outer")
    assert await store.load("s1") is None


@pytest.mark.asyncio
async def test_question_and_hint_idempotency_round_trip():
    store = InMemorySessionStore()
    now = datetime.utcnow()
    question = QuestionRecord(
        question_id="q1", session_id="s1", slot_id="sl1",
        question_generation_key="s1:q1", purpose="first_question",
        text="Tell me about a project.", source="fallback", created_at=now,
    )
    hint = HintRecord(
        hint_id="h1", session_id="s1", hint_idempotency_key="s1:h1",
        question_id="q1", text="Think about ownership.", hints_used=1, created_at=now,
    )
    async with store.transaction():
        await store.put_question(question)
        await store.put_hint(hint)

    stored_question = await store.get_question_by_key("s1", "s1:q1")
    stored_hint = await store.get_hint_by_key("s1", "s1:h1")
    assert stored_question is not None
    assert stored_question.model_dump() == question.model_dump()
    assert stored_hint is not None
    assert stored_hint.model_dump() == hint.model_dump()
    assert await store.get_question_by_key("other", "s1:q1") is None
    assert await store.get_hint_by_key("other", "s1:h1") is None


@pytest.mark.asyncio
async def test_turn_command_round_trip_and_double_complete_is_safe():
    store = InMemorySessionStore()
    now = datetime.utcnow()
    command = TurnCommandRecord(
        session_id="s1", idempotency_key="k1", status="pending",
        created_at=now, updated_at=now,
    )
    async with store.transaction():
        await store.put_turn_command(command)

    stored = await store.get_turn_command("s1", "k1")
    assert stored is not None
    assert stored.status == "pending"
    assert await store.get_turn_command("other", "k1") is None

    await store.complete_turn_command("s1", "k1", {"accepted": True})
    completed = await store.get_turn_command("s1", "k1")
    assert completed.status == "complete"
    assert completed.result == {"accepted": True}

    await store.complete_turn_command("s1", "k1", {"corrupted": True})
    again = await store.get_turn_command("s1", "k1")
    assert again.status == "complete"
    assert again.result == {"accepted": True}


@pytest.mark.asyncio
async def test_update_report_requires_matching_outcome():
    store = InMemorySessionStore()
    now = datetime.utcnow()
    report = ReportRecord(
        report_id="r1", session_id="s1", outcome="draft",
        created_at=now, updated_at=now,
    )
    async with store.transaction():
        await store.put_report(report)

    ready = report.model_copy(update={"outcome": "ready"})
    assert await store.update_report(ready, expected_outcome="final") is False
    assert await store.update_report(ready, expected_outcome="draft") is True
    assert await store.update_report(ready, expected_outcome="draft") is False
    stored = await store.get_report("r1")
    assert stored.outcome == "ready"
