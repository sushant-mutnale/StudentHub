from backend.interview_engine.contracts.enums import ConfidenceBand, Level, NextAction
from backend.interview_engine.domain.scoring import (
    InstanceFact,
    confidence_for,
    counts_for_scoring,
    decide_next_action,
    is_slot_complete,
    level_for,
    move_difficulty,
)


def fact(signal, qid="q1", contradiction=False):
    return InstanceFact(competency="c", question_id=qid, signal=signal, contradiction=contradiction)


def test_only_new_sufficient_or_incomplete_instances_count():
    assert counts_for_scoring("sufficient", "new") is True
    assert counts_for_scoring("incomplete", "new") is True
    assert counts_for_scoring("off_topic", "new") is False
    assert counts_for_scoring("sufficient", "same") is False


def test_slot_completes_on_sufficient_or_spent_allowance():
    assert is_slot_complete("sufficient", 0, 1) is True
    assert is_slot_complete("incomplete", 0, 1) is False
    assert is_slot_complete("incomplete", 1, 1) is True
    assert is_slot_complete("off_topic", 1, 1) is True


def test_next_action_clarification_wins():
    assert decide_next_action(
        clarification=True, slot_complete=True, has_further_slot=True,
        signal="sufficient", allowance_remaining=1,
    ) == NextAction.AWAIT_ANSWER


def test_next_action_end_on_last_complete_slot():
    assert decide_next_action(
        clarification=False, slot_complete=True, has_further_slot=False,
        signal="sufficient", allowance_remaining=0,
    ) == NextAction.END


def test_next_action_follow_up_requires_incomplete_and_allowance():
    assert decide_next_action(
        clarification=False, slot_complete=False, has_further_slot=True,
        signal="incomplete", allowance_remaining=1,
    ) == NextAction.FOLLOW_UP
    assert decide_next_action(
        clarification=False, slot_complete=False, has_further_slot=True,
        signal="sufficient", allowance_remaining=1,
    ) == NextAction.NEXT_SLOT


def test_confidence_ordered_rule():
    assert confidence_for([]) == ConfidenceBand.NOT_ASSESSED
    assert confidence_for([fact("sufficient")]) == ConfidenceBand.LOW
    assert confidence_for([fact("sufficient"), fact("sufficient", "q2")]) == ConfidenceBand.MEDIUM
    assert confidence_for([fact("sufficient", "q1", True), fact("sufficient", "q2")]) == ConfidenceBand.LOW
    three = [fact("sufficient", "q1"), fact("sufficient", "q2"), fact("sufficient", "q3")]
    assert confidence_for(three) == ConfidenceBand.HIGH
    repeated = [fact("sufficient", "q1"), fact("sufficient", "q1"), fact("sufficient", "q1")]
    assert confidence_for(repeated) == ConfidenceBand.MEDIUM


def test_level_total_function():
    assert level_for([]) == Level.NOT_ASSESSED
    assert level_for([fact("incomplete")]) == Level.EMERGING
    assert level_for([fact("sufficient"), fact("incomplete", "q2")]) == Level.PROFICIENT
    assert level_for([fact("incomplete"), fact("incomplete", "q2"), fact("sufficient", "q3")]) == Level.DEVELOPING
    assert level_for([fact("sufficient"), fact("sufficient", "q2")]) == Level.STRONG


def test_contradiction_caps_confidence_but_not_level():
    facts = [fact("sufficient", "q1", True), fact("sufficient", "q2"), fact("sufficient", "q3")]
    assert confidence_for(facts) == ConfidenceBand.LOW
    assert level_for(facts) == Level.STRONG


def test_difficulty_moves_one_step_and_never_reverses():
    assert move_difficulty("intermediate", "sufficient", False, 0) == ("advanced", 1)
    assert move_difficulty("intermediate", "incomplete", True, 0) == ("novice", -1)
    assert move_difficulty("intermediate", "incomplete", False, 0) == ("intermediate", 0)
    assert move_difficulty("intermediate", "off_topic", True, 0) == ("intermediate", 0)
    assert move_difficulty("intermediate", "incomplete", True, 1) == ("intermediate", 1)
    assert move_difficulty("novice", "incomplete", True, 0) == ("novice", 0)
    assert move_difficulty("advanced", "sufficient", False, 0) == ("advanced", 0)
