import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import (
    StartSessionCommand,
    SubmitTurnCommand,
    SubmitTurnResult,
)
from backend.interview_engine.contracts.records import Analysis
from backend.interview_engine.errors import DeviceConflict
from backend.interview_engine.ports.capabilities import GeneratedQuestion


def _build(script=None, store=None, generator=None):
    store = store or InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=ScriptedAnalyzer(script or []),
        generator=generator or ScriptedQuestionGenerator(),
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


def _cmd(result, key="turn-1", text="I led the migration and cut errors by half."):
    return SubmitTurnCommand(
        candidate_id="c1",
        session_id=result.session_id,
        device_id="d1",
        fencing_token=result.fencing_token,
        turn_idempotency_key=key,
        kind="answer",
        text=text,
        question_id=result.question_id,
    )


async def _drive_to_final_slot(engine, start, turns=8):
    result = await engine.submit_turn(_cmd(start))
    for index in range(turns):
        cmd = _cmd(start, key=f"turn-{index + 2}")
        cmd.question_id = result.question_id
        result = await engine.submit_turn(cmd)
    return result


@pytest.mark.asyncio
async def test_sufficient_answer_returns_next_question_and_records_evidence():
    engine, store = _build()
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    assert result.next_action == "next_slot"
    assert result.question != start.first_question
    assert result.question_id != start.question_id
    assert result.status == "in_progress"
    evidence = await store.evidence_for_session(start.session_id)
    assert len(evidence) == 1
    assert evidence[0].competency == "problem_solving"
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-2"
    assert record.question_pending is False
    assert record.outstanding_question == result.question


@pytest.mark.asyncio
async def test_duplicate_turn_returns_stored_result_without_second_turn():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start))
    second = await engine.submit_turn(_cmd(start))
    assert second.dict() == first.dict()
    assert await store.count_turns(start.session_id) == 1
    assert len(await store.evidence_for_session(start.session_id)) == 1


@pytest.mark.asyncio
async def test_incomplete_answer_asks_follow_up_and_spends_allowance():
    engine, store = _build(
        [Analysis(signal="incomplete", instance="new", substantively_deficient=True)]
    )
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start, text="Not much to say."))
    assert result.next_action == "follow_up"
    assert result.question == (
        "What alternatives did you consider before choosing that approach, and why did you reject them?"
    )
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-1"
    assert record.follow_up_used == {"problem_solving-1": 1}


@pytest.mark.asyncio
async def test_second_incomplete_after_allowance_advances_slot():
    engine, store = _build(
        [
            Analysis(signal="incomplete", instance="new", substantively_deficient=True),
            Analysis(signal="incomplete", instance="new", substantively_deficient=True),
        ]
    )
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start))
    second_cmd = _cmd(start, key="turn-2", text="Still not much.")
    second_cmd.question_id = first.question_id
    second = await engine.submit_turn(second_cmd)
    assert first.next_action == "follow_up"
    assert second.next_action == "next_slot"
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-2"
    assert record.follow_up_used == {"problem_solving-1": 1}


@pytest.mark.asyncio
async def test_clarification_returns_same_question_and_no_evidence():
    engine, store = _build()
    start = await _started(engine)
    cmd = _cmd(start, key="clarify-1")
    cmd.kind = "clarification_request"
    cmd.text = "What do you mean by concrete?"
    result = await engine.submit_turn(cmd)
    assert result.next_action == "await_answer"
    assert result.question == start.first_question
    assert result.question_id == start.question_id
    assert await store.evidence_for_session(start.session_id) == []


@pytest.mark.asyncio
async def test_final_sufficient_answer_ends_and_allocates_report():
    engine, store = _build([Analysis(signal="sufficient", instance="new") for _ in range(10)])
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    for index in range(9):
        cmd = _cmd(start, key=f"turn-{index + 2}")
        cmd.question_id = result.question_id
        result = await engine.submit_turn(cmd)
    assert result.next_action == "end"
    assert result.status == "completed"
    assert result.report_id
    assert result.report_outcome == "evaluating"
    report = await store.get_report(result.report_id)
    assert report.outcome == "evaluating"
    outbox_types = [o.event_type for o in store._outbox]
    assert outbox_types.count("interview_engine.report.requested") == 1


@pytest.mark.asyncio
async def test_wrong_device_is_rejected():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.device_id = "d2"
    with pytest.raises(DeviceConflict):
        await engine.submit_turn(cmd)


@pytest.mark.asyncio
async def test_question_mismatch_is_rejected():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.question_id = "not-the-outstanding-question"
    with pytest.raises(Exception) as exc:
        await engine.submit_turn(cmd)
    assert getattr(exc.value, "code", "") == "question_mismatch"


@pytest.mark.asyncio
async def test_end_path_writes_complete_command_record_in_one_transaction():
    engine, store = _build()
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    for index in range(9):
        cmd = _cmd(start, key=f"turn-{index + 2}")
        cmd.question_id = result.question_id
        result = await engine.submit_turn(cmd)
    assert result.next_action == "end"
    command = await store.get_turn_command(start.session_id, "turn-10")
    assert command.status == "complete"
    assert command.result["next_action"] == "end"
    replay = await engine.submit_turn(_cmd(start, key="turn-10"))
    assert replay.dict() == result.dict()
    assert await store.count_turns(start.session_id) == 10


class _CrashOnCompleteStore(InMemorySessionStore):
    def __init__(self):
        super().__init__()
        self.armed = False
        self.completions = 0

    async def complete_turn_command(self, session_id, key, result):
        if self.armed:
            self.completions += 1
            raise RuntimeError("crash")
        await super().complete_turn_command(session_id, key, result)


@pytest.mark.asyncio
async def test_end_path_survives_a_crash_before_the_second_transaction():
    store = _CrashOnCompleteStore()
    engine, _ = _build(store=store)
    start = await _started(engine)
    result = await _drive_to_final_slot(engine, start)
    store.armed = True
    terminal_cmd = _cmd(start, key="turn-10")
    terminal_cmd.question_id = result.question_id
    terminal = await engine.submit_turn(terminal_cmd)
    assert terminal.next_action == "end"
    assert store.completions == 0
    record = await store.load(start.session_id)
    assert record.status == "completed"
    command = await store.get_turn_command(start.session_id, "turn-10")
    assert command.status == "complete"
    assert command.result["next_action"] == "end"


@pytest.mark.asyncio
async def test_clarification_emits_turn_submitted_then_clarification_replied():
    engine, store = _build()
    start = await _started(engine)
    cmd = _cmd(start, key="clarify-1")
    cmd.kind = "clarification_request"
    cmd.text = "What do you mean by concrete?"
    await engine.submit_turn(cmd)
    events = [e for e in store._events if e.session_id == start.session_id]
    assert [e.event_type for e in events[3:]] == ["TurnSubmitted", "ClarificationReplied"]
    assert [e.event_sequence for e in events[3:]] == [4, 5]


@pytest.mark.asyncio
async def test_answer_events_are_ordered():
    engine, store = _build()
    start = await _started(engine)
    await engine.submit_turn(_cmd(start))
    events = [e for e in store._events if e.session_id == start.session_id]
    assert [e.event_type for e in events[3:]] == [
        "TurnSubmitted",
        "TurnAnalysisRequested",
        "QuestionAsked",
    ]


class _FlakyQuestionStore(InMemorySessionStore):
    def __init__(self):
        super().__init__()
        self.fail_next_question_write = False

    async def put_question(self, question):
        if self.fail_next_question_write:
            self.fail_next_question_write = False
            raise RuntimeError("crash")
        await super().put_question(question)


class _FailOnceGenerator:
    def __init__(self):
        self.calls = 0

    async def generate(self, request):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("provider down")
        return GeneratedQuestion(text=request.slot.fallback_question, source="fallback")


@pytest.mark.asyncio
async def test_pending_turn_recovers_question_on_retry():
    store = _FlakyQuestionStore()
    engine, _ = _build(store=store, generator=_FailOnceGenerator())
    start = await _started(engine)
    store.fail_next_question_write = True
    with pytest.raises(RuntimeError):
        await engine.submit_turn(_cmd(start))
    pending = await store.get_turn_command(start.session_id, "turn-1")
    assert pending.status == "pending"
    result = await engine.submit_turn(_cmd(start))
    stored = await store.get_turn_command(start.session_id, "turn-1")
    assert stored.status == "complete"
    assert SubmitTurnResult(**stored.result).dict() == result.dict()
    assert result.next_action == "next_slot"
    record = await store.load(start.session_id)
    assert result.question == record.blueprint.slot("problem_solving-2").fallback_question
    assert await store.count_turns(start.session_id) == 1
