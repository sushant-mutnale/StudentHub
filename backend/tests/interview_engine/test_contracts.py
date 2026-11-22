from datetime import datetime

from backend.interview_engine.contracts import enums
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.messages import SessionView, SubmitTurnResult
from backend.interview_engine.contracts.records import SessionRecord


def _slot():
    return BlueprintSlot(
        slot_id="ps-1",
        competency="problem_solving",
        dimension="problem_solving",
        difficulty="intermediate",
        intent="Describe a concrete problem you solved.",
        fallback_question="Tell me about a concrete problem you solved.",
        follow_up_question="What would you do differently?",
        clarification_text="Share a specific past situation.",
        hint_text="Pick one project and describe the constraint.",
    )


def test_signal_enum_is_exactly_the_typed_set():
    assert {s.value for s in enums.Signal} == {"sufficient", "incomplete", "off_topic"}
    assert {s.value for s in enums.InstanceKind} == {"new", "same"}


def test_next_action_enum_has_no_removed_value():
    assert {a.value for a in enums.NextAction} == {
        "await_answer",
        "follow_up",
        "next_slot",
        "end",
    }


def test_session_record_round_trips_through_dict():
    blueprint = Blueprint(groups=[BlueprintGroup(group_id="g1", competency="problem_solving", slots=[_slot()])])
    record = SessionRecord(
        session_id="s1",
        candidate_id="c1",
        interview_type="behavioral",
        mode="practice",
        status="planned",
        version=0,
        event_sequence=0,
        last_applied_sequence=0,
        fencing_token="t1",
        device_id="d1",
        blueprint=blueprint,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    restored = SessionRecord.parse_obj(record.dict())
    assert restored.blueprint.groups[0].slots[0].slot_id == "ps-1"
    assert restored.follow_up_used == {}
    assert restored.question_pending is True


def test_session_view_reports_missing_question():
    view = SessionView(
        session_id="s1",
        status="planned",
        version=0,
        question_pending=True,
        outstanding_question=None,
        report_id=None,
        report_outcome=None,
        fencing_token="t1",
    )
    assert view.question_pending is True
    assert view.outstanding_question is None


def test_submit_turn_result_has_no_score_field():
    result = SubmitTurnResult(
        session_id="s1",
        status="in_progress",
        next_action="next_slot",
        question="Q2",
        question_id="q2",
        version=3,
    )
    assert not hasattr(result, "score")
    assert result.dict().get("score") is None
