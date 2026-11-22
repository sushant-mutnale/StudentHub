import asyncio
from datetime import datetime

import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand
from backend.interview_engine.contracts.records import EventRecord, SessionRecord
from backend.interview_engine.domain.behavioral_blueprint import build_behavioral_blueprint
from backend.interview_engine.errors import (
    DeviceConflict,
    InvalidState,
    NotOwner,
    SessionExists,
    SessionNotFound,
    UnsupportedInterviewType,
    UnsupportedMode,
)
from backend.interview_engine.ports.capabilities import GeneratedQuestion


def _engine(store=None, generator=None, generation_timeout_seconds=None):
    store = store or InMemorySessionStore()
    kwargs = {}
    if generation_timeout_seconds is not None:
        kwargs["generation_timeout_seconds"] = generation_timeout_seconds
    return (
        InterviewEngine(
            store=store,
            lease=InMemoryLease(),
            clock=SystemClock(),
            ids=UuidIds(),
            analyzer=ScriptedAnalyzer([]),
            generator=generator or ScriptedQuestionGenerator(),
            evaluator=DeterministicEvaluator(),
            **kwargs,
        ),
        store,
    )


def _start(client_request_id="req-1", interview_type="behavioral", mode="practice"):
    return StartSessionCommand(
        candidate_id="c1",
        interview_type=interview_type,
        mode=mode,
        device_id="d1",
        client_request_id=client_request_id,
        role="Senior Engineer",
        company="Acme",
    )


@pytest.mark.asyncio
async def test_start_creates_session_question_event_and_outbox():
    engine, store = _engine()
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question.startswith("Walk me through")
    assert result.status == "in_progress"
    assert result.version == 1
    assert record.status == "in_progress"
    assert record.question_pending is False
    assert record.outstanding_question == result.first_question
    assert record.current_slot_id == "problem_solving-1"
    assert record.blueprint.blueprint_version == "behavioral-v1"
    assert record.fencing_token == result.fencing_token
    events = [e for e in store._events if e.session_id == result.session_id]
    assert [e.event_type for e in events] == ["SessionCreated", "SessionStarted", "QuestionAsked"]
    assert [e.event_sequence for e in events] == [1, 2, 3]
    outbox = [o for o in store._outbox if o.event_type == "interview_engine.question.requested"]
    assert len(outbox) == 1
    assert outbox[0].payload["question_generation_key"].endswith(":0:first_question")


@pytest.mark.asyncio
async def test_start_is_idempotent_by_client_request_id():
    engine, store = _engine()
    first = await engine.start(_start())
    second = await engine.start(_start())
    assert first.session_id == second.session_id
    assert second.first_question == first.first_question
    assert len(store._sessions) == 1


@pytest.mark.asyncio
async def test_new_request_id_against_active_session_returns_session_exists():
    engine, store = _engine()
    first = await engine.start(_start("req-1"))
    with pytest.raises(SessionExists) as exc:
        await engine.start(_start("req-2"))
    assert exc.value.session_id == first.session_id


@pytest.mark.asyncio
async def test_unsupported_type_is_rejected():
    engine, _ = _engine()
    with pytest.raises(UnsupportedInterviewType):
        await engine.start(_start(interview_type="dsa"))


@pytest.mark.asyncio
async def test_unsupported_mode_is_rejected():
    engine, _ = _engine()
    with pytest.raises(UnsupportedMode):
        await engine.start(_start(mode="formal"))


@pytest.mark.asyncio
async def test_generator_failure_persists_fallback_question():
    class BrokenGenerator:
        async def generate(self, request):
            raise RuntimeError("provider down")

    engine, store = _engine(generator=BrokenGenerator())
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question == record.blueprint.slot("problem_solving-1").fallback_question
    assert record.question_pending is False
    assert record.status == "in_progress"


@pytest.mark.asyncio
async def test_ensure_question_is_idempotent_by_generation_key():
    engine, store = _engine()
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    request = {
        "slot_id": "problem_solving-1",
        "purpose": "first_question",
        "session_version_at_request": 0,
        "question_generation_key": f"{record.session_id}:0:first_question",
    }
    again = await engine.ensure_question(record.session_id, request)
    assert again.question_id == result.question_id
    assert len(store._questions) == 1
    events = [e for e in store._events if e.session_id == record.session_id]
    assert [e.event_type for e in events] == ["SessionCreated", "SessionStarted", "QuestionAsked"]
    assert [e.event_sequence for e in events] == [1, 2, 3]


@pytest.mark.asyncio
async def test_load_owned_rejects_missing_and_foreign_sessions():
    engine, _ = _engine()
    result = await engine.start(_start())
    owned = await engine.load_owned(result.session_id, "c1")
    assert owned.session_id == result.session_id
    with pytest.raises(SessionNotFound):
        await engine.load_owned("missing", "c1")
    with pytest.raises(NotOwner):
        await engine.load_owned(result.session_id, "c2")


@pytest.mark.asyncio
async def test_start_retry_recovers_crashed_planned_session():
    engine, store = _engine()
    blueprint = build_behavioral_blueprint("practice", "Senior Engineer", None)
    now = datetime.utcnow()
    seeded = SessionRecord(
        session_id="seeded-session",
        candidate_id="c1",
        interview_type="behavioral",
        mode="practice",
        status="planned",
        version=0,
        event_sequence=1,
        last_applied_sequence=1,
        fencing_token="token-1",
        device_id="d1",
        blueprint=blueprint,
        client_request_id="req-1",
        role="Senior Engineer",
        company="Acme",
        question_pending=True,
        created_at=now,
        updated_at=now,
    )
    await store.insert(seeded)
    await store.append_event(
        EventRecord(
            event_id="event-1",
            session_id="seeded-session",
            event_sequence=1,
            event_type="SessionCreated",
            payload={"mode": "practice", "interview_type": "behavioral"},
            created_at=now,
        )
    )
    result = await engine.start(_start())
    assert result.session_id == "seeded-session"
    assert result.status == "in_progress"
    assert result.version == 1
    assert len(store._sessions) == 1
    events = [e for e in store._events if e.session_id == "seeded-session"]
    assert [e.event_type for e in events] == ["SessionCreated", "SessionStarted", "QuestionAsked"]


@pytest.mark.asyncio
async def test_generator_timeout_falls_back_to_blueprint_question():
    class SlowGenerator:
        async def generate(self, request):
            await asyncio.sleep(5)
            return GeneratedQuestion(text="Too late to matter?", source="generated")

    engine, store = _engine(generator=SlowGenerator(), generation_timeout_seconds=0.05)
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question == record.blueprint.slot("problem_solving-1").fallback_question
    assert result.status == "in_progress"


@pytest.mark.asyncio
async def test_invalid_generated_text_falls_back():
    class IncompleteGenerator:
        async def generate(self, request):
            return GeneratedQuestion(text="Tell me about a time", source="generated")

    engine, store = _engine(generator=IncompleteGenerator())
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question == record.blueprint.slot("problem_solving-1").fallback_question
    assert record.outstanding_question == record.blueprint.slot("problem_solving-1").fallback_question


@pytest.mark.asyncio
async def test_lease_conflict_raises_device_conflict():
    class ConflictingLease(InMemoryLease):
        async def acquire(self, session_id, device_id, token, ttl_seconds):
            return False

    engine, store = _engine()
    engine.lease = ConflictingLease()
    with pytest.raises(DeviceConflict):
        await engine.start(_start())
    assert len(store._sessions) == 0


@pytest.mark.asyncio
async def test_lease_is_released_when_session_write_fails():
    engine, store = _engine()

    async def failing_insert(record):
        raise RuntimeError("mongo down")

    store.insert = failing_insert
    with pytest.raises(RuntimeError):
        await engine.start(_start())
    assert engine.lease._leases == {}


@pytest.mark.asyncio
async def test_ensure_question_rejects_malformed_request():
    engine, _ = _engine()
    with pytest.raises(InvalidState):
        await engine.ensure_question("s", {})
