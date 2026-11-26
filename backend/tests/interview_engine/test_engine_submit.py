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
from backend.interview_engine.contracts.records import Analysis, TurnCommandRecord
from backend.interview_engine.errors import (
    DeviceConflict,
    QuestionPendingConflict,
    VersionConflict,
)
from backend.interview_engine.ports.capabilities import GeneratedQuestion


def _build(script=None, store=None, generator=None, analyzer=None):
    store = store or InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=analyzer or ScriptedAnalyzer(script or []),
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


class _ExplodingAnalyzer:
    async def analyze(self, request):
        raise AssertionError("analyzer must not run for clarifications")


@pytest.mark.asyncio
async def test_clarification_reply_is_persisted_and_returned():
    engine, store = _build()
    start = await _started(engine)
    cmd = _cmd(start, key="clarify-1")
    cmd.kind = "clarification_request"
    cmd.text = "What do you mean by concrete?"
    result = await engine.submit_turn(cmd)
    record = await store.load(start.session_id)
    assert result.reply == record.blueprint.slot("problem_solving-1").clarification_text
    turns = await store.turns_for_session(start.session_id)
    assert turns[-1].reply == result.reply
    replied = [e for e in store._events if e.event_type == "ClarificationReplied"]
    assert replied[-1].payload["reply"] == result.reply


@pytest.mark.asyncio
async def test_clarification_skips_the_analyzer():
    engine, store = _build(analyzer=_ExplodingAnalyzer())
    start = await _started(engine)
    cmd = _cmd(start, key="clarify-1")
    cmd.kind = "clarification_request"
    cmd.text = "What do you mean by concrete?"
    result = await engine.submit_turn(cmd)
    assert result.next_action == "await_answer"
    assert await store.evidence_for_session(start.session_id) == []
    record = await store.load(start.session_id)
    assert record.follow_up_used == {}


@pytest.mark.asyncio
async def test_session_version_bumps_exactly_once_per_turn():
    engine, store = _build()
    start = await _started(engine)
    assert start.version == 1
    answered = await engine.submit_turn(_cmd(start))
    record = await store.load(start.session_id)
    assert record.version == answered.version
    assert record.version == 3
    clarify = _cmd(start, key="clarify-1")
    clarify.kind = "clarification_request"
    clarify.text = "What do you mean by concrete?"
    clarify.question_id = answered.question_id
    reply = await engine.submit_turn(clarify)
    record = await store.load(start.session_id)
    assert record.version == reply.version
    assert record.version == 4


@pytest.mark.asyncio
async def test_new_key_on_question_pending_session_conflicts():
    engine, store = _build()
    start = await _started(engine)
    record = await store.load(start.session_id)
    record.question_pending = True
    record.outstanding_question = None
    record.current_question_id = None
    record.pending_question_request = {
        "slot_id": "problem_solving-1",
        "purpose": "first_question",
        "question_generation_key": f"{start.session_id}:0:first_question",
        "session_version_at_request": 0,
    }
    await store.replace(record, expected_version=record.version)
    with pytest.raises(QuestionPendingConflict):
        await engine.submit_turn(_cmd(start, key="turn-2"))


@pytest.mark.asyncio
async def test_stale_expected_version_is_rejected():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.expected_version = 99
    with pytest.raises(VersionConflict):
        await engine.submit_turn(cmd)


@pytest.mark.asyncio
async def test_stale_version_wins_over_stale_question_id():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.expected_version = 99
    cmd.question_id = "bogus"
    with pytest.raises(VersionConflict):
        await engine.submit_turn(cmd)


@pytest.mark.asyncio
async def test_same_instance_answer_records_no_evidence():
    engine, store = _build([Analysis(signal="sufficient", instance="same")])
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    assert result.next_action == "next_slot"
    assert await store.evidence_for_session(start.session_id) == []
    assert await store.count_turns(start.session_id) == 1
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-2"


@pytest.mark.asyncio
async def test_end_emits_session_completed_with_reason():
    engine, store = _build()
    start = await _started(engine)
    result = await _drive_to_final_slot(engine, start)
    cmd = _cmd(start, key="turn-10")
    cmd.question_id = result.question_id
    terminal = await engine.submit_turn(cmd)
    assert terminal.next_action == "end"
    events = [e for e in store._events if e.session_id == start.session_id]
    assert events[-1].event_type == "SessionCompleted"
    assert events[-1].payload["reason"] == "candidate_completed"
    assert events[-1].payload["report_id"] == terminal.report_id


def _simulate_post_question_crash(store, session_id, key):
    command = store._commands[f"{session_id}:{key}"]
    store._commands[f"{session_id}:{key}"] = TurnCommandRecord(
        session_id=command.session_id,
        idempotency_key=command.idempotency_key,
        status="pending",
        result=None,
        created_at=command.created_at,
        updated_at=command.updated_at,
    )
    store._sessions[session_id].pending_question_request = None


@pytest.mark.asyncio
async def test_pending_turn_recovers_after_question_already_persisted():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start))
    assert first.next_action == "next_slot"
    record = await store.load(start.session_id)
    outstanding = record.outstanding_question
    outstanding_id = record.current_question_id
    _simulate_post_question_crash(store, start.session_id, "turn-1")
    retry = await engine.submit_turn(_cmd(start))
    assert retry.question == outstanding
    assert retry.question_id == outstanding_id
    assert retry.next_action == "next_slot"
    assert await store.count_turns(start.session_id) == 1
    stored = await store.get_turn_command(start.session_id, "turn-1")
    assert stored.status == "complete"
    assert SubmitTurnResult(**stored.result).dict() == retry.dict()


@pytest.mark.asyncio
async def test_pending_turn_follow_up_purpose_is_preserved():
    engine, store = _build(
        [Analysis(signal="incomplete", instance="new", substantively_deficient=True)]
    )
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start, text="Not much to say."))
    assert first.next_action == "follow_up"
    record = await store.load(start.session_id)
    outstanding = record.outstanding_question
    _simulate_post_question_crash(store, start.session_id, "turn-1")
    retry = await engine.submit_turn(_cmd(start, text="Not much to say."))
    assert retry.next_action == "follow_up"
    assert retry.question == outstanding
    assert retry.question_id == first.question_id
    assert await store.count_turns(start.session_id) == 1
