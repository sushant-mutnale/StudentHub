import copy
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Tuple

from ..contracts.records import (
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)

_MAX_ATTEMPTS = 5

_Snapshot = Tuple[
    Dict[str, SessionRecord],
    List[EventRecord],
    List[TurnRecord],
    List[EvidenceRecord],
    Dict[str, QuestionRecord],
    Dict[str, HintRecord],
    Dict[str, TurnCommandRecord],
    Dict[str, ReportRecord],
    List[OutboxRecord],
    Dict[str, str],
]


class InMemorySessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}
        self._events: List[EventRecord] = []
        self._turns: List[TurnRecord] = []
        self._evidence: List[EvidenceRecord] = []
        self._questions: Dict[str, QuestionRecord] = {}
        self._hints: Dict[str, HintRecord] = {}
        self._commands: Dict[str, TurnCommandRecord] = {}
        self._reports: Dict[str, ReportRecord] = {}
        self._outbox: List[OutboxRecord] = []
        self._outbox_errors: Dict[str, str] = {}
        self._snapshots: List[_Snapshot] = []

    @asynccontextmanager
    async def transaction(self):
        self._snapshots.append(
            copy.deepcopy(
                (self._sessions, self._events, self._turns, self._evidence, self._questions,
                 self._hints, self._commands, self._reports, self._outbox, self._outbox_errors)
            )
        )
        try:
            yield self
        except Exception:
            (self._sessions, self._events, self._turns, self._evidence, self._questions,
             self._hints, self._commands, self._reports, self._outbox,
             self._outbox_errors) = self._snapshots[-1]
            raise
        finally:
            self._snapshots.pop()

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        record = self._sessions.get(session_id)
        return copy.deepcopy(record) if record else None

    async def load_by_client_request_id(
        self, candidate_id: str, client_request_id: str
    ) -> Optional[SessionRecord]:
        for record in self._sessions.values():
            if (
                record.candidate_id == candidate_id
                and record.client_request_id == client_request_id
            ):
                return copy.deepcopy(record)
        return None

    async def find_active(
        self, candidate_id: str, interview_type: str, mode: str
    ) -> Optional[SessionRecord]:
        for record in self._sessions.values():
            if (
                record.candidate_id == candidate_id
                and record.interview_type == interview_type
                and record.mode == mode
                and record.status in ("planned", "in_progress", "paused")
            ):
                return copy.deepcopy(record)
        return None

    async def insert(self, record: SessionRecord) -> None:
        self._sessions[record.session_id] = copy.deepcopy(record)

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        current = self._sessions.get(record.session_id)
        if current is None or current.version != expected_version:
            return False
        self._sessions[record.session_id] = copy.deepcopy(record)
        return True

    async def append_event(self, event: EventRecord) -> None:
        self._events.append(copy.deepcopy(event))

    async def append_turn(self, turn: TurnRecord) -> None:
        self._turns.append(copy.deepcopy(turn))

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        return sum(
            1 for t in self._turns
            if t.session_id == session_id and (kind is None or t.kind == kind)
        )

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        return [copy.deepcopy(t) for t in self._turns if t.session_id == session_id]

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        self._evidence.append(copy.deepcopy(evidence))

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        return [copy.deepcopy(e) for e in self._evidence if e.session_id == session_id]

    async def put_question(self, question: QuestionRecord) -> None:
        self._questions[question.question_generation_key] = copy.deepcopy(question)

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        question = self._questions.get(key)
        if question and question.session_id == session_id:
            return copy.deepcopy(question)
        return None

    async def questions_for_session(self, session_id: str) -> List[QuestionRecord]:
        return [
            copy.deepcopy(item)
            for item in self._questions.values()
            if item.session_id == session_id
        ]

    async def put_hint(self, hint: HintRecord) -> None:
        self._hints[hint.hint_idempotency_key] = copy.deepcopy(hint)

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        hint = self._hints.get(key)
        if hint and hint.session_id == session_id:
            return copy.deepcopy(hint)
        return None

    def _command_key(self, session_id: str, key: str) -> str:
        return f"{session_id}:{key}"

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        command = self._commands.get(self._command_key(session_id, key))
        if command and command.session_id == session_id:
            return copy.deepcopy(command)
        return None

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        self._commands[self._command_key(command.session_id, command.idempotency_key)] = (
            copy.deepcopy(command)
        )

    async def turn_commands_for_session(self, session_id: str) -> List[TurnCommandRecord]:
        return [
            copy.deepcopy(item)
            for key, item in self._commands.items()
            if item.session_id == session_id
        ]

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        command = self._commands.get(self._command_key(session_id, key))
        if command is None or command.session_id != session_id:
            return
        if command.status == "complete":
            return
        command.status = "complete"
        command.result = copy.deepcopy(result)

    async def put_report(self, report: ReportRecord) -> None:
        self._reports[report.report_id] = copy.deepcopy(report)

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        report = self._reports.get(report_id)
        return copy.deepcopy(report) if report else None

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        current = self._reports.get(report.report_id)
        if current is None or current.outcome != expected_outcome:
            return False
        self._reports[report.report_id] = copy.deepcopy(report)
        return True

    async def append_outbox(self, record: OutboxRecord) -> None:
        self._outbox.append(copy.deepcopy(record))

    @property
    def outbox_errors(self) -> Dict[str, str]:
        return dict(self._outbox_errors)

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        claimed = []
        for record in self._outbox:
            if len(claimed) >= limit:
                break
            if record.status in ("pending", "failed") and record.attempts < _MAX_ATTEMPTS:
                record.status = "processing"
                record.attempts += 1
                record.worker_id = worker_id
                claimed.append(copy.deepcopy(record))
        return claimed

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        for record in self._outbox:
            if record.outbox_id == outbox_id:
                record.status = "processed"

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        for record in self._outbox:
            if record.outbox_id == outbox_id:
                record.status = "failed"
                self._outbox_errors[outbox_id] = error
