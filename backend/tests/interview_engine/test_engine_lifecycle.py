import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.enums import Mode, SessionStatus
from backend.interview_engine.contracts.messages import (
    EndSessionCommand,
    PauseSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from backend.interview_engine.errors import (
    CommandIdRequired,
    HintLimitReached,
    HintUnavailable,
    NoReport,
    PauseLimitReached,
    QuestionPendingConflict,
)


def _build(store=None, engine_class=InterviewEngine):
    store = store or InMemorySessionStore()
    engine = engine_class(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=ScriptedAnalyzer([]),
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
            client_request_id="req-1",
            role="Senior Engineer",
            company="Acme",
        )
    )


def _hint(start, key="hint-1", question_id=None):
    return RequestHintCommand(
        candidate_id="c1",
        session_id=start.session_id,
        device_id="d1",
        fencing_token=start.fencing_token,
        hint_idempotency_key=key,
        question_id=start.question_id if question_id is None else question_id,
    )


def _pause(start, command_id="p1", fencing_token=None):
    return PauseSessionCommand(
        candidate_id="c1",
        session_id=start.session_id,
        device_id="d1",
        fencing_token=start.fencing_token if fencing_token is None else fencing_token,
        command_id=command_id,
    )


def _resume(start, device_id="d1", command_id="r1"):
    return ResumeSessionCommand(
        candidate_id="c1",
        session_id=start.session_id,
        device_id=device_id,
        command_id=command_id,
    )


def _end(start, command_id="end-1"):
    return EndSessionCommand(
        candidate_id="c1",
        session_id=start.session_id,
        device_id="d1",
        fencing_token=start.fencing_token,
        end_command_id=command_id,
    )


async def _answer(
    engine,
    start,
    question_id,
    key="turn-1",
    text="I led the migration and cut errors by half.",
):
    return await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=start.session_id,
            device_id="d1",
            fencing_token=start.fencing_token,
            turn_idempotency_key=key,
            kind="answer",
            text=text,
            question_id=question_id,
        )
    )


async def _force(store, session_id, **fields):
    record = await store.load(session_id)
    for key, value in fields.items():
        setattr(record, key, value)
    async with store.transaction():
        assert await store.replace(record, expected_version=record.version)
    return record


def _events(store, session_id, event_type=None):
    return [
        event
        for event in store._events
        if event.session_id == session_id
        and (event_type is None or event.event_type == event_type)
    ]


@pytest.mark.asyncio
async def test_hint_returns_authored_text_and_is_idempotent():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.request_hint(_hint(start))
    second = await engine.request_hint(_hint(start))
    assert first.hint == second.hint
    assert first.hints_used == 1
    assert second.hints_used == 1
    assert first.remaining == 1
    assert first.question_id == start.question_id
    record = await store.load(start.session_id)
    assert record.hint_count == 1


@pytest.mark.asyncio
async def test_hint_budget_is_bounded():
    engine, _ = _build()
    start = await _started(engine)
    await engine.request_hint(_hint(start, "h1"))
    await engine.request_hint(_hint(start, "h2"))
    with pytest.raises(HintLimitReached):
        await engine.request_hint(_hint(start, "h3"))


@pytest.mark.asyncio
async def test_pause_and_resume_takeover_bumps_token_not_version_direction():
    engine, store = _build()
    start = await _started(engine)
    paused = await engine.pause(_pause(start, "p1"))
    assert paused.status == "paused"
    resumed = await engine.resume(_resume(start, device_id="d2"))
    assert resumed.status == "in_progress"
    assert resumed.fencing_token != start.fencing_token
    record = await store.load(start.session_id)
    assert record.device_id == "d2"
    assert record.fencing_token == resumed.fencing_token
    assert record.disconnect_count == 1


@pytest.mark.asyncio
async def test_resume_takes_lease_from_other_device():
    engine, _ = _build()
    start = await _started(engine)
    resumed = await engine.resume(_resume(start, device_id="d2"))
    assert resumed.fencing_token != start.fencing_token
    assert resumed.question == start.first_question
    assert resumed.question_id == start.question_id


@pytest.mark.asyncio
async def test_end_is_idempotent_and_allocates_report_once():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.end(_end(start, "end-1"))
    second = await engine.end(_end(start, "end-2"))
    assert first.report_id == second.report_id
    assert first.report_outcome == "evaluating"
    assert len(store._reports) == 1
    assert list(store._reports.values())[0].report_id == first.report_id


@pytest.mark.asyncio
async def test_report_is_evaluating_until_outbox_drain_then_ready():
    engine, _ = _build()
    start = await _started(engine)
    ended = await engine.end(_end(start))
    evaluating = await engine.get_report("c1", ended.report_id)
    assert evaluating.outcome == "evaluating"
    assert evaluating.body is None
    processed = await engine.drain_outbox()
    assert processed >= 1
    ready = await engine.get_report("c1", ended.report_id)
    assert ready.outcome == "ready"
    assert ready.body is not None
    assert "competencies" in ready.body
    assert "score" not in ready.body


@pytest.mark.asyncio
async def test_feedback_on_abandoned_session_has_no_report():
    engine, store = _build()
    start = await _started(engine)
    record = await store.load(start.session_id)
    record.status = "abandoned"
    async with store.transaction():
        await store.replace(record, expected_version=record.version)
    with pytest.raises(NoReport):
        await engine.get_report("c1", None)


@pytest.mark.asyncio
async def test_hint_after_question_advanced_still_returns_the_original_hint():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.request_hint(_hint(start, "hint-1"))
    answered = await _answer(engine, start, start.question_id)
    assert answered.question_id != start.question_id
    second = await engine.request_hint(_hint(start, "hint-1"))
    assert second.hint == first.hint
    assert second.question_id == start.question_id
    assert second.question_id != answered.question_id
    assert second.hints_used == 1
    assert len(store._hints) == 1
    hint_events = _events(store, start.session_id, "HintProvided")
    assert len(hint_events) == 1
    assert hint_events[0].payload == {"question_id": start.question_id, "hints_used": 1}
    record = await store.load(start.session_id)
    assert record.hint_count == 1


@pytest.mark.asyncio
async def test_hint_on_pending_question_conflicts():
    engine, store = _build()
    start = await _started(engine)
    await _force(
        store,
        start.session_id,
        question_pending=True,
        outstanding_question=None,
        current_question_id=None,
        pending_question_request={
            "slot_id": "problem_solving-1",
            "purpose": "first_question",
            "question_generation_key": f"{start.session_id}:0:first_question",
            "session_version_at_request": 0,
        },
    )
    with pytest.raises(QuestionPendingConflict):
        await engine.request_hint(_hint(start))


@pytest.mark.asyncio
async def test_hint_on_formal_session_is_unavailable():
    engine, store = _build()
    start = await _started(engine)
    await _force(
        store,
        start.session_id,
        mode=Mode.FORMAL.value,
        status=SessionStatus.IN_PROGRESS.value,
    )
    with pytest.raises(HintUnavailable):
        await engine.request_hint(_hint(start))


@pytest.mark.asyncio
async def test_pause_is_idempotent_by_command_id():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.pause(_pause(start, "p1"))
    second = await engine.pause(_pause(start, "p1"))
    assert second.dict() == first.dict()
    assert first.version == second.version
    assert len(_events(store, start.session_id, "SessionPaused")) == 1


@pytest.mark.asyncio
async def test_pause_twice_with_different_command_ids_is_rejected_for_formal_only():
    engine, _ = _build()
    start = await _started(engine)
    first = await engine.pause(_pause(start, "p1"))
    resumed = await engine.resume(_resume(start, command_id="r1"))
    second = await engine.pause(_pause(start, "p2", fencing_token=resumed.fencing_token))
    assert resumed.status == "in_progress"
    assert second.status == "paused"
    assert second.version > first.version

    formal_engine, formal_store = _build()
    formal_start = await _started(formal_engine)
    await _force(
        formal_store,
        formal_start.session_id,
        mode=Mode.FORMAL.value,
        status=SessionStatus.IN_PROGRESS.value,
        pause_count=1,
    )
    with pytest.raises(PauseLimitReached):
        await formal_engine.pause(_pause(formal_start, "p1"))


@pytest.mark.asyncio
async def test_resume_on_paused_session_without_command_id_requires_one():
    engine, _ = _build()
    start = await _started(engine)
    await engine.pause(_pause(start, "p1"))
    with pytest.raises(CommandIdRequired):
        await engine.resume(_resume(start, command_id=None))


@pytest.mark.asyncio
async def test_resume_is_idempotent_by_command_id():
    engine, store = _build()
    start = await _started(engine)
    await engine.pause(_pause(start, "p1"))
    first = await engine.resume(_resume(start, command_id="r1"))
    second = await engine.resume(_resume(start, command_id="r1"))
    assert second.dict() == first.dict()
    assert len(_events(store, start.session_id, "SessionResumed")) == 1


@pytest.mark.asyncio
async def test_resume_plain_takeover_does_not_bump_version():
    engine, store = _build()
    start = await _started(engine)
    before = await store.load(start.session_id)
    resumed = await engine.resume(_resume(start, device_id="d2"))
    record = await store.load(start.session_id)
    assert record.version == before.version
    assert resumed.version == before.version
    assert record.device_id == "d2"
    assert len(_events(store, start.session_id, "SessionLeaseTakenOver")) == 1


@pytest.mark.asyncio
async def test_resume_emits_session_resumed_then_lease_taken_over():
    engine, store = _build()
    start = await _started(engine)
    await engine.pause(_pause(start, "p1"))
    await engine.resume(_resume(start, device_id="d2", command_id="r1"))
    tail = [event.event_type for event in _events(store, start.session_id)][-2:]
    assert tail == ["SessionResumed", "SessionLeaseTakenOver"]


@pytest.mark.asyncio
async def test_end_emits_session_completed_with_reason_and_is_idempotent_by_command_id():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.end(_end(start, "end-1"))
    completed = _events(store, start.session_id, "SessionCompleted")
    assert len(completed) == 1
    assert completed[0].payload["reason"] == "candidate_completed"
    assert completed[0].payload["report_id"] == first.report_id
    command = await store.get_turn_command(start.session_id, "end:end-1")
    assert command.status == "complete"
    second = await engine.end(_end(start, "end-1"))
    assert second.dict() == first.dict()
    assert len(_events(store, start.session_id, "SessionCompleted")) == 1
    assert len(store._reports) == 1


class _FailingReportEngine(InterviewEngine):
    async def build_report_body(self, report_id):
        raise RuntimeError("report assembly failed")


@pytest.mark.asyncio
async def test_outbox_failure_is_marked_failed_and_not_retried_forever():
    engine, store = _build(engine_class=_FailingReportEngine)
    start = await _started(engine)
    await engine.end(_end(start))
    report_rows = [
        item
        for item in store._outbox
        if item.event_type == "interview_engine.report.requested"
    ]
    assert len(report_rows) == 1
    assert await engine.drain_outbox() == 1
    assert report_rows[0].status == "failed"
    assert report_rows[0].attempts == 1
    assert store.outbox_errors[report_rows[0].outbox_id] == "report assembly failed"
    for _ in range(4):
        assert await engine.drain_outbox() == 0
    assert report_rows[0].attempts == 5
    assert report_rows[0].status == "failed"
    assert await engine.drain_outbox() == 0
    assert report_rows[0].attempts == 5


@pytest.mark.asyncio
async def test_report_body_has_no_score_key():
    engine, _ = _build()
    start = await _started(engine)
    first = await _answer(engine, start, start.question_id, "turn-1")
    second = await _answer(
        engine,
        start,
        first.question_id,
        "turn-2",
        "I measured the rollout, found the regression, and fixed it.",
    )
    assert second.status == "in_progress"
    ended = await engine.end(_end(start))
    await engine.drain_outbox()
    report = await engine.get_report("c1", ended.report_id)
    body = report.body
    assert "score" not in body
    assert body["competencies"]
    for entry in body["competencies"]:
        assert "level" in entry
        assert "confidence" in entry
    supported = [entry for entry in body["competencies"] if entry["instance_count"] > 0]
    assert supported
    for entry in supported:
        assert len(entry["excerpts"]) >= 2
