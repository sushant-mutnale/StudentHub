from datetime import datetime, timedelta

from backend.interview_engine.application.report_builder import build_report, sentence_excerpt
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.records import EvidenceRecord, SessionRecord, TurnRecord
from backend.interview_engine.contracts.report import EvaluatorOutput


def _slot(slot_id, competency):
    return BlueprintSlot(
        slot_id=slot_id, competency=competency, dimension=competency, difficulty="intermediate",
        intent="i", fallback_question="q", follow_up_question="f",
        clarification_text="c", hint_text="h",
    )


def _record(hint_count=1, groups=None):
    blueprint = Blueprint(groups=groups or [
        BlueprintGroup(group_id="ps", competency="problem_solving", slots=[_slot("ps-1", "problem_solving")]),
        BlueprintGroup(group_id="cm", competency="communication", slots=[_slot("cm-1", "communication")]),
    ])
    started = datetime(2026, 11, 1, 10, 0, 0)
    return SessionRecord(
        session_id="s1", candidate_id="c1", interview_type="behavioral", mode="practice",
        status="completed", version=5, event_sequence=5, last_applied_sequence=5,
        fencing_token="t1", device_id="d1", blueprint=blueprint, role="Senior Engineer",
        company="Acme", report_id="r1", report_outcome="evaluating", hint_count=hint_count,
        created_at=started, updated_at=started, started_at=started,
        completed_at=started + timedelta(minutes=12),
    )


def _turn(turn_id, slot_id, text):
    return TurnRecord(
        turn_id=turn_id, session_id="s1", sequence=1, kind="answer", question_id=f"q-{turn_id}",
        slot_id=slot_id, text=text, idempotency_key=f"k-{turn_id}", device_id="d1",
        created_at=datetime.utcnow(),
    )


def _evidence(turn_id, slot_id, competency, signal="sufficient", contradiction=False, instance="new"):
    return EvidenceRecord(
        evidence_id=f"e-{turn_id}", session_id="s1", turn_id=turn_id, question_id=f"q-{turn_id}",
        slot_id=slot_id, competency=competency, signal=signal, instance=instance,
        contradiction=contradiction, difficulty="intermediate", created_at=datetime.utcnow(),
    )


def _competency(report, name):
    return next(c for c in report.competencies if c.competency == name)


def test_sentence_excerpt_keeps_two_sentences():
    text = "First sentence. Second sentence. Third sentence."
    assert sentence_excerpt(text) == "First sentence. Second sentence."


def test_report_has_no_composite_score_and_discloses_ai():
    report = build_report(_record(), [], [], EvaluatorOutput())
    assert "score" not in report.dict()
    assert "overall_score" not in report.dict()
    assert report.disclosure["ai_generated_questions"] is True
    assert report.disclosure["no_proctoring"] is True
    assert report.integrity["blueprint_version"] == "behavioral-v1"
    assert report.duration_seconds == 720


def test_report_with_no_evidence_marks_every_competency_not_assessed():
    turns = [_turn("t1", "ps-1", "I did a thing. It worked.")]
    report = build_report(_record(), [], turns, EvaluatorOutput())
    assert {c.level for c in report.competencies} == {"not_assessed"}
    assert all(c.excerpts == [] for c in report.competencies)
    ps = _competency(report, "problem_solving")
    assert ps.confidence == "not_assessed"
    assert any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_two_sufficient_instances_yield_strong_medium_with_two_excerpts():
    turns = [
        _turn("t1", "ps-1", "I led the migration. We cut errors by half."),
        _turn("t2", "ps-1", "I validated the result. Error rates stayed low."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.level == "strong"
    assert ps.confidence == "medium"
    assert len(ps.excerpts) == 2
    assert ps.excerpts[0].text == "I led the migration. We cut errors by half."


def test_single_instance_two_sentences_yields_two_excerpts():
    turns = [_turn("t1", "ps-1", "Only one answer here. It is short.")]
    evidence = [_evidence("t1", "ps-1", "problem_solving")]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.confidence == "low"
    assert len(ps.excerpts) == 2
    assert [e.text for e in ps.excerpts] == ["Only one answer here.", "It is short."]
    assert {e.turn_id for e in ps.excerpts} == {"t1"}
    assert any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_single_instance_one_sentence_yields_one_verbatim_excerpt():
    turns = [_turn("t1", "ps-1", "Only one sentence here")]
    evidence = [_evidence("t1", "ps-1", "problem_solving")]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert len(ps.excerpts) == 1
    assert ps.excerpts[0].text == "Only one sentence here"
    assert any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_contradiction_adds_conflicting_evidence_limitation():
    turns = [
        _turn("t1", "ps-1", "A. B."),
        _turn("t2", "ps-1", "C. D."),
        _turn("t3", "ps-1", "E. F."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving", contradiction=True),
        _evidence("t2", "ps-1", "problem_solving"),
        _evidence("t3", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.confidence == "low"
    assert ps.level == "strong"
    assert any(l.category == "conflicting_evidence" for l in ps.limitations)


def test_contradicting_turn_excerpt_is_included_first():
    turns = [
        _turn("t1", "ps-1", "Plain answer. With two sentences."),
        _turn("t2", "ps-1", "Conflicting answer. With two sentences."),
        _turn("t3", "ps-1", "Another answer. With two sentences."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving", contradiction=True),
        _evidence("t3", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.excerpts[0].turn_id == "t2"


def test_contradiction_on_non_scoring_evidence_does_not_claim_low_cap():
    turns = [
        _turn("t1", "ps-1", "A. B."),
        _turn("t2", "ps-1", "C. D."),
        _turn("t3", "ps-1", "E. F."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
        _evidence("t3", "ps-1", "problem_solving", contradiction=True, signal="off_topic"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.confidence == "medium"
    assert not any(l.category == "conflicting_evidence" for l in ps.limitations)


def test_off_topic_answer_adds_time_coverage_not_insufficient_evidence():
    turns = [
        _turn("t1", "ps-1", "A. B."),
        _turn("t2", "ps-1", "C. D."),
        _turn("t3", "ps-1", "Something unrelated. Nothing relevant."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
        _evidence("t3", "ps-1", "problem_solving", signal="off_topic"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.level == "strong"
    assert any(l.category == "time_coverage" for l in ps.limitations)
    assert not any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_scored_competency_without_transcript_adds_mode_technical_limitation():
    evidence = [_evidence("t1", "ps-1", "problem_solving")]
    report = build_report(_record(), evidence, [], EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.level == "strong"
    assert ps.excerpts == []
    assert any(l.category == "mode_technical" for l in ps.limitations)


def test_hint_assistance_limitation_is_reported_once_at_body_level():
    turns = [_turn("t1", "ps-1", "A. B."), _turn("t2", "ps-1", "C. D.")]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(hint_count=2), evidence, turns, EvaluatorOutput())
    hints = [l for l in report.limitations if l.category == "hint_assistance"]
    assert len(hints) == 1
    assert "2" in hints[0].detail
    assert not any(
        l.category == "hint_assistance" for c in report.competencies for l in c.limitations
    )


def test_body_limitations_are_deduplicated():
    groups = [
        BlueprintGroup(group_id="ps", competency="problem_solving", slots=[_slot("ps-1", "problem_solving")]),
        BlueprintGroup(group_id="cm", competency="communication", slots=[_slot("cm-1", "communication")]),
    ]
    report = build_report(_record(hint_count=0, groups=groups), [], [], EvaluatorOutput())
    keys = [(l.category, l.detail) for l in report.limitations]
    assert len(keys) == len(set(keys))


def test_duplicate_groups_for_one_competency_emit_one_report_entry():
    groups = [
        BlueprintGroup(group_id="ps", competency="problem_solving", slots=[_slot("ps-1", "problem_solving")]),
        BlueprintGroup(group_id="ps2", competency="problem_solving", slots=[_slot("ps-2", "problem_solving")]),
    ]
    turns = [
        _turn("t1", "ps-1", "A. B."),
        _turn("t2", "ps-2", "C. D."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-2", "problem_solving"),
    ]
    report = build_report(_record(hint_count=0, groups=groups), evidence, turns, EvaluatorOutput())
    assert [c.competency for c in report.competencies] == ["problem_solving"]
    assert report.competencies[0].level == "strong"


def test_partial_transcript_loss_keeps_one_excerpt_and_flags_mode_technical():
    turns = [_turn("t1", "ps-1", "Only one sentence here")]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert len(ps.excerpts) == 1
    assert any(l.category == "mode_technical" for l in ps.limitations)


def test_two_facts_with_one_two_sentence_turn_reach_two_excerpts_without_flag():
    turns = [_turn("t1", "ps-1", "First sentence here. Second sentence here.")]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert len(ps.excerpts) == 2
    assert not any(l.category == "mode_technical" for l in ps.limitations)


def test_excerpted_non_scoring_contradiction_gets_neutral_limitation():
    turns = [
        _turn("t1", "ps-1", "Plain answer. With two sentences."),
        _turn("t2", "ps-1", "Conflicting answer. With two sentences."),
        _turn("t3", "ps-1", "Another answer. With two sentences."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving", contradiction=True, instance="same"),
        _evidence("t3", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert ps.confidence == "medium"
    assert ps.excerpts[0].turn_id == "t2"
    conflicting = [l for l in ps.limitations if l.category == "conflicting_evidence"]
    assert len(conflicting) == 1
    assert "low" not in conflicting[0].detail


def test_report_limits_excerpts_to_three():
    turns = [_turn(f"t{i}", "ps-1", f"Sentence {i}. More {i}.") for i in range(1, 5)]
    evidence = [_evidence(f"t{i}", "ps-1", "problem_solving") for i in range(1, 5)]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = _competency(report, "problem_solving")
    assert len(ps.excerpts) == 3
