from datetime import datetime
from typing import Optional

from ..contracts.blueprint import BlueprintSlot
from ..contracts.enums import NextAction, SessionStatus
from ..contracts.records import Analysis, EvidenceRecord, SessionRecord, TurnRecord
from .scoring import counts_for_scoring, decide_next_action, is_slot_complete

_TERMINAL = {
    SessionStatus.COMPLETED.value,
    SessionStatus.ABANDONED.value,
    SessionStatus.EXPIRED.value,
}


def is_terminal_status(status: str) -> bool:
    return status in _TERMINAL


_TRANSITIONS = {
    SessionStatus.PLANNED.value: {
        SessionStatus.IN_PROGRESS.value,
        SessionStatus.COMPLETED.value,
        SessionStatus.ABANDONED.value,
        SessionStatus.EXPIRED.value,
    },
    SessionStatus.IN_PROGRESS.value: {
        SessionStatus.PAUSED.value,
        SessionStatus.COMPLETED.value,
        SessionStatus.ABANDONED.value,
    },
    SessionStatus.PAUSED.value: {
        SessionStatus.IN_PROGRESS.value,
        SessionStatus.COMPLETED.value,
        SessionStatus.ABANDONED.value,
    },
}


class Session:
    def __init__(self, record: SessionRecord):
        self.record = record

    @classmethod
    def from_record(cls, record: SessionRecord) -> "Session":
        return cls(SessionRecord.parse_obj(record.dict()))

    def to_record(self) -> SessionRecord:
        return self.record

    def is_terminal(self) -> bool:
        return self.record.status in _TERMINAL

    def can_accept_turn(self) -> bool:
        return (
            self.record.status == SessionStatus.IN_PROGRESS.value
            and not self.record.question_pending
            and self.record.outstanding_question is not None
        )

    def bump(self) -> int:
        self.record.version += 1
        self.record.updated_at = datetime.utcnow()
        return self.record.version

    def next_sequence(self) -> int:
        self.record.event_sequence += 1
        self.record.last_applied_sequence = self.record.event_sequence
        return self.record.event_sequence

    def slot(self) -> BlueprintSlot:
        if not self.record.current_slot_id:
            raise ValueError("no current slot")
        return self.record.blueprint.slot(self.record.current_slot_id)

    def slot_allowance(self) -> int:
        return self.slot().allowance(self.record.mode)

    def follow_up_used_for(self, slot_id: str) -> int:
        return self.record.follow_up_used.get(slot_id, 0)

    def has_further_slot(self) -> bool:
        return self.record.plan_position + 1 < len(self.record.blueprint.ordered_slots())

    def advance_slot(self) -> None:
        """Move the plan position forward and clear the question.

        This is a plan-position mutation only: it does not bump ``version`` or
        append an event. Callers that persist the change must call ``bump()``
        once themselves; ``apply_answer`` already does so.
        """
        self.record.plan_position += 1
        ordered = self.record.blueprint.ordered_slots()
        if self.record.plan_position < len(ordered):
            self.record.current_slot_id = ordered[self.record.plan_position].slot_id
            self.record.current_question_id = None
            self.record.outstanding_question = None
            self.record.question_pending = True

    def set_question(self, question_id: str, text: str, slot_id: str, pending: bool = False) -> None:
        """Make ``text`` the outstanding question for ``slot_id``.

        Does not bump ``version``; the caller persists with a single ``bump()``.
        """
        if self.is_terminal():
            raise ValueError("session is terminal")
        self.record.current_question_id = question_id
        self.record.outstanding_question = text
        self.record.current_slot_id = slot_id
        self.record.question_pending = pending
        if not pending and self.record.status == SessionStatus.PLANNED.value:
            self._require_transition(SessionStatus.IN_PROGRESS.value)
            self.record.status = SessionStatus.IN_PROGRESS.value
            self.record.started_at = self.record.started_at or datetime.utcnow()

    def set_question_pending(self, request: Optional[dict]) -> None:
        """Clear the outstanding question and record a pending generation request.

        Does not bump ``version``; the caller persists with a single ``bump()``.
        """
        self.record.question_pending = True
        self.record.pending_question_request = request
        self.record.outstanding_question = None
        self.record.current_question_id = None

    def apply_clarification(self, turn: TurnRecord, reply: str) -> None:
        if not self.can_accept_turn():
            raise ValueError("session cannot accept a turn")
        self.bump()

    def apply_answer(
        self,
        turn: TurnRecord,
        analysis: Analysis,
        evidence: Optional[EvidenceRecord],
        competency: str,
    ) -> NextAction:
        if not self.can_accept_turn():
            raise ValueError("session cannot accept a turn")
        if evidence is not None and not counts_for_scoring(evidence.signal, evidence.instance):
            raise ValueError("evidence does not count for scoring")
        slot = self.slot()
        allowance = slot.allowance(self.record.mode)
        used = self.follow_up_used_for(slot.slot_id)
        slot_complete = is_slot_complete(analysis.signal, used, allowance)
        action = decide_next_action(
            clarification=False,
            slot_complete=slot_complete,
            has_further_slot=self.has_further_slot(),
            signal=analysis.signal,
            allowance_remaining=max(allowance - used, 0),
        )
        if action == NextAction.FOLLOW_UP:
            self.record.follow_up_used[slot.slot_id] = used + 1
            self.set_question_pending(
                {
                    "slot_id": slot.slot_id,
                    "purpose": "follow_up",
                    "question_generation_key": f"{self.record.session_id}:{self.record.version}:follow_up",
                    "session_version_at_request": self.record.version,
                }
            )
        elif action == NextAction.NEXT_SLOT:
            self.advance_slot()
            next_slot = self.record.blueprint.ordered_slots()[self.record.plan_position]
            self.set_question_pending(
                {
                    "slot_id": next_slot.slot_id,
                    "purpose": "next_question",
                    "question_generation_key": f"{self.record.session_id}:{self.record.version}:next_question",
                    "session_version_at_request": self.record.version,
                }
            )
        elif action == NextAction.END:
            self.record.report_id = self.record.report_id or f"report-{self.record.session_id}"
            outcome = "suppressed" if not self.record.consent.evaluation else "evaluating"
            self.begin_completion(self.record.report_id, outcome)
            return action
        self.bump()
        return action

    def begin_completion(self, report_id: str, outcome: str) -> None:
        self._require_transition(SessionStatus.COMPLETED.value)
        self.record.status = SessionStatus.COMPLETED.value
        self.record.report_id = report_id
        self.record.report_outcome = outcome
        self.record.completed_at = datetime.utcnow()
        self.record.question_pending = False
        self.record.outstanding_question = None
        self.bump()

    def mark_paused(self) -> None:
        self._require_transition(SessionStatus.PAUSED.value)
        self.record.status = SessionStatus.PAUSED.value
        self.record.pause_count += 1
        self.record.pause_started_at = datetime.utcnow()
        self.bump()

    def mark_resumed(self) -> None:
        if self.record.status != SessionStatus.PAUSED.value:
            raise ValueError("only a paused session can be resumed")
        self._require_transition(SessionStatus.IN_PROGRESS.value)
        if self.record.pause_started_at:
            self.record.total_pause_seconds += int(
                (datetime.utcnow() - self.record.pause_started_at).total_seconds()
            )
            self.record.pause_started_at = None
        self.record.status = SessionStatus.IN_PROGRESS.value
        self.bump()

    def _require_transition(self, target: str) -> None:
        if target not in _TRANSITIONS.get(self.record.status, set()):
            raise ValueError(f"illegal transition {self.record.status} -> {target}")
