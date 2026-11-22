from dataclasses import dataclass
from typing import Sequence, Tuple

from ..contracts.enums import ConfidenceBand, Level, NextAction, Signal

_DIFFICULTY_ORDER = ("novice", "intermediate", "advanced")


@dataclass(frozen=True)
class InstanceFact:
    competency: str
    question_id: str
    signal: str
    contradiction: bool = False


def counts_for_scoring(signal: str, instance: str) -> bool:
    return instance == "new" and signal in (Signal.SUFFICIENT.value, Signal.INCOMPLETE.value)


def is_slot_complete(signal: str, follow_up_used: int, allowance: int) -> bool:
    return signal == Signal.SUFFICIENT.value or follow_up_used >= allowance


def decide_next_action(
    *,
    clarification: bool,
    slot_complete: bool,
    has_further_slot: bool,
    signal: str,
    allowance_remaining: int,
) -> NextAction:
    if clarification:
        return NextAction.AWAIT_ANSWER
    if slot_complete:
        return NextAction.NEXT_SLOT if has_further_slot else NextAction.END
    if allowance_remaining > 0 and signal in (Signal.INCOMPLETE.value, Signal.OFF_TOPIC.value):
        return NextAction.FOLLOW_UP
    return NextAction.NEXT_SLOT if has_further_slot else NextAction.END


def confidence_for(facts: Sequence[InstanceFact]) -> ConfidenceBand:
    if not facts:
        return ConfidenceBand.NOT_ASSESSED
    if any(f.contradiction for f in facts):
        return ConfidenceBand.LOW
    if len(facts) == 1:
        return ConfidenceBand.LOW
    distinct_questions = {f.question_id for f in facts}
    if (
        len(facts) >= 3
        and len(distinct_questions) >= 3
        and all(f.signal == Signal.SUFFICIENT.value for f in facts)
    ):
        return ConfidenceBand.HIGH
    return ConfidenceBand.MEDIUM


def level_for(facts: Sequence[InstanceFact]) -> Level:
    total = len(facts)
    if total == 0:
        return Level.NOT_ASSESSED
    sufficient = sum(1 for f in facts if f.signal == Signal.SUFFICIENT.value)
    if sufficient == 0:
        return Level.EMERGING
    if sufficient * 2 < total:
        return Level.DEVELOPING
    if sufficient < total:
        return Level.PROFICIENT
    return Level.STRONG


def move_difficulty(
    current: str,
    signal: str,
    substantively_deficient: bool,
    last_direction: int,
) -> Tuple[str, int]:
    index = _DIFFICULTY_ORDER.index(current)
    if (
        signal == Signal.SUFFICIENT.value
        and last_direction >= 0
        and index < len(_DIFFICULTY_ORDER) - 1
    ):
        return _DIFFICULTY_ORDER[index + 1], 1
    if (
        signal == Signal.INCOMPLETE.value
        and substantively_deficient
        and last_direction <= 0
        and index > 0
    ):
        return _DIFFICULTY_ORDER[index - 1], -1
    return current, last_direction
