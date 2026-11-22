from datetime import datetime, timedelta

import pytest

from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.enums import NextAction
from backend.interview_engine.contracts.records import Analysis, EvidenceRecord, SessionRecord, TurnRecord
from backend.interview_engine.domain.session import Session


def _slot(slot_id, competency):
    return BlueprintSlot(
        slot_id=slot_id,
        competency=competency,
        dimension=competency,
        difficulty="intermediate",
        intent=f"intent {slot_id}",
        fallback_question=f"question {slot_id}",
        follow_up_question=f"follow up {slot_id}",
        clarification_text="clarify",
        hint_text="hint",
    )


def _session():
    blueprint = Blueprint(
        groups=[
            BlueprintGroup(group_id="g1", competency="a", slots=[_slot("a1", "a"), _slot("a2", "a")]),
            BlueprintGroup(group_id="g2", competency="b", slots=[_slot("b1", "b"), _slot("b2", "b")]),
        ]
    )
    record = SessionRecord(
        session_id="s1", candidate_id="c1", interview_type="behavioral", mode="practice",
        status="in_progress", version=1, event_sequence=1, last_applied_sequence=1,
        fencing_token="t1", device_id="d1", blueprint=blueprint,
        current_slot_id="a1", current_question_id="q1", outstanding_question="question a1",
        question_pending=False, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    return Session.from_record(record)


def _turn(kind="answer", text="answer text"):
    return TurnRecord(
        turn_id="t-1", session_id="s1", sequence=1, kind=kind, question_id="q1",
        slot_id="a1", text=text, idempotency_key="k1", device_id="d1",
        created_at=datetime.utcnow(),
    )


def _evidence(turn_id="t-1", signal="sufficient", instance="new"):
    return EvidenceRecord(
        evidence_id="e1", session_id="s1", turn_id=turn_id, question_id="q1", slot_id="a1",
        competency="a", signal=signal, instance=instance, difficulty="intermediate",
        created_at=datetime.utcnow(),
    )


def test_advance_slot_moves_plan_position_and_clears_question():
    session = _session()
    session.advance_slot()
    assert session.record.plan_position == 1
    assert session.record.current_slot_id == "a2"
    assert session.record.outstanding_question is None
    assert session.record.question_pending is True


def test_sufficient_answer_advances_slot():
    session = _session()
    action = session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")
    assert action == NextAction.NEXT_SLOT
    assert session.record.plan_position == 1
    assert session.record.follow_up_used == {}


def test_incomplete_answer_emits_follow_up_and_spends_allowance():
    session = _session()
    action = session.apply_answer(
        _turn(), Analysis(signal="incomplete", instance="new", substantively_deficient=True), _evidence(), "a"
    )
    assert action == NextAction.FOLLOW_UP
    assert session.record.follow_up_used == {"a1": 1}
    assert session.record.question_pending is True
    assert session.record.plan_position == 0


def test_follow_up_answer_completes_slot_even_when_incomplete():
    session = _session()
    session.apply_answer(_turn(), Analysis(signal="incomplete", instance="new"), _evidence(), "a")
    session.set_question("q2", "follow up a1", "a1", pending=False)
    action = session.apply_answer(
        _turn(), Analysis(signal="incomplete", instance="new"), _evidence(), "a"
    )
    assert action == NextAction.NEXT_SLOT


def test_off_topic_with_allowance_triggers_follow_up_but_records_nothing():
    session = _session()
    action = session.apply_answer(
        _turn(), Analysis(signal="off_topic", instance="same"), None, "a"
    )
    assert action == NextAction.FOLLOW_UP
    assert session.record.follow_up_used == {"a1": 1}


def test_last_slot_sufficient_ends_and_allocates_report():
    session = _session()
    session.record.plan_position = 3
    session.record.current_slot_id = "b2"
    session.record.current_question_id = "q4"
    session.record.outstanding_question = "question b2"
    action = session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "b")
    assert action == NextAction.END
    assert session.is_terminal() is True
    assert session.record.report_id is not None
    assert session.record.report_outcome == "evaluating"


def test_clarification_keeps_question_and_does_not_record_evidence():
    session = _session()
    session.apply_clarification(_turn(kind="clarification_request"), "clarify")
    assert session.record.current_question_id == "q1"
    assert session.record.outstanding_question == "question a1"
    assert session.record.question_pending is False


def test_terminal_session_rejects_answers():
    session = _session()
    session.begin_completion("r1", "evaluating")
    assert session.is_terminal() is True
    assert session.can_accept_turn() is False


def test_slot_helpers_report_allowance_and_remaining_slots():
    session = _session()
    assert session.slot().slot_id == "a1"
    assert session.slot_allowance() == 1
    assert session.follow_up_used_for("a1") == 0
    assert session.has_further_slot() is True
    session.record.mode = "formal"
    assert session.slot_allowance() == 0


def test_state_change_bumps_version_without_consuming_event_sequence():
    session = _session()
    session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")
    assert session.record.version == 2
    assert session.record.event_sequence == 1
    assert session.record.last_applied_sequence == 1


def test_lease_takeover_advances_event_sequence_without_bumping_version():
    session = _session()
    version = session.record.version
    assert session.next_sequence() == 2
    assert session.record.event_sequence == 2
    assert session.record.last_applied_sequence == 2
    assert session.record.version == version


def test_answer_without_outstanding_question_is_rejected():
    session = _session()
    session.set_question_pending(None)
    assert session.can_accept_turn() is False
    with pytest.raises(ValueError):
        session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")


def test_non_counting_evidence_is_rejected_and_records_no_instance():
    session = _session()
    with pytest.raises(ValueError):
        session.apply_answer(
            _turn(),
            Analysis(signal="incomplete", instance="same"),
            _evidence(signal="incomplete", instance="same"),
            "a",
        )
    assert session.record.follow_up_used == {}
    assert session.record.version == 1


def test_from_record_does_not_mutate_the_source_record():
    blueprint = Blueprint(
        groups=[BlueprintGroup(group_id="g1", competency="a", slots=[_slot("a1", "a"), _slot("a2", "a")])]
    )
    record = SessionRecord(
        session_id="s1", candidate_id="c1", interview_type="behavioral", mode="practice",
        status="in_progress", version=1, event_sequence=1, last_applied_sequence=1,
        fencing_token="t1", device_id="d1", blueprint=blueprint,
        current_slot_id="a1", current_question_id="q1", outstanding_question="question a1",
        question_pending=False, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session = Session.from_record(record)
    session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")
    assert record.version == 1
    assert record.plan_position == 0
    assert record.follow_up_used == {}
    assert session.to_record() is session.record


def test_pause_and_resume_track_counters_and_restore_status():
    session = _session()
    session.mark_paused()
    assert session.record.status == "paused"
    assert session.record.pause_count == 1
    assert session.record.pause_started_at is not None
    session.record.pause_started_at = datetime.utcnow() - timedelta(seconds=5)
    session.mark_resumed()
    assert session.record.status == "in_progress"
    assert session.record.total_pause_seconds >= 5
    assert session.record.pause_started_at is None


def test_planned_session_starts_on_first_question_and_may_complete():
    session = _session()
    session.record.status = "planned"
    session.record.current_question_id = None
    session.record.outstanding_question = None
    session.set_question("q1", "question a1", "a1", pending=False)
    assert session.record.status == "in_progress"
    assert session.record.started_at is not None

    planned = _session()
    planned.record.status = "planned"
    planned.begin_completion("r1", "evaluating")
    assert planned.record.status == "completed"


def test_illegal_transition_is_rejected():
    session = _session()
    session.begin_completion("r1", "evaluating")
    with pytest.raises(ValueError):
        session.mark_paused()
    with pytest.raises(ValueError):
        session.mark_resumed()


def test_started_sessions_never_expire():
    session = _session()
    with pytest.raises(ValueError):
        session._require_transition("expired")

    session.mark_paused()
    with pytest.raises(ValueError):
        session._require_transition("expired")


def test_planned_session_may_expire_or_be_abandoned():
    session = _session()
    session.record.status = "planned"
    session._require_transition("expired")
    session._require_transition("abandoned")


def test_in_progress_and_paused_may_be_abandoned_or_completed():
    session = _session()
    session._require_transition("abandoned")
    session._require_transition("completed")

    session.mark_paused()
    session._require_transition("abandoned")
    session._require_transition("completed")


def test_paused_session_completes_and_in_progress_cannot_resume():
    paused = _session()
    paused.mark_paused()
    paused.begin_completion("r1", "evaluating")
    assert paused.record.status == "completed"

    running = _session()
    with pytest.raises(ValueError):
        running.mark_resumed()

    planned = _session()
    planned.record.status = "planned"
    with pytest.raises(ValueError):
        planned.mark_resumed()


def test_terminal_statuses_have_no_outgoing_transitions():
    for status in ("completed", "abandoned", "expired"):
        session = _session()
        session.record.status = status
        for target in ("in_progress", "paused", "completed", "abandoned", "expired"):
            with pytest.raises(ValueError):
                session._require_transition(target)


def test_set_question_alone_does_not_bump_but_apply_answer_bumps_once():
    session = _session()
    session.set_question("q2", "question a2", "a2", pending=False)
    session.set_question_pending(None)
    session.advance_slot()
    assert session.record.version == 1

    session = _session()
    session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")
    assert session.record.version == 2


def test_clarification_rejected_when_session_cannot_accept_a_turn():
    pending = _session()
    pending.set_question_pending(None)
    with pytest.raises(ValueError):
        pending.apply_clarification(_turn(kind="clarification_request"), "clarify")

    paused = _session()
    paused.mark_paused()
    with pytest.raises(ValueError):
        paused.apply_clarification(_turn(kind="clarification_request"), "clarify")
