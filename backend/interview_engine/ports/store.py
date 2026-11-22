from contextlib import AbstractAsyncContextManager
from typing import List, Optional, Protocol

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


class SessionStore(Protocol):
    def transaction(self) -> AbstractAsyncContextManager["SessionStore"]:
        ...

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        ...

    async def load_by_client_request_id(
        self, candidate_id: str, client_request_id: str
    ) -> Optional[SessionRecord]:
        ...

    async def find_active(
        self, candidate_id: str, interview_type: str, mode: str
    ) -> Optional[SessionRecord]:
        ...

    async def insert(self, record: SessionRecord) -> None:
        ...

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        ...

    async def append_event(self, event: EventRecord) -> None:
        ...

    async def append_turn(self, turn: TurnRecord) -> None:
        ...

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        ...

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        ...

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        ...

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        ...

    async def put_question(self, question: QuestionRecord) -> None:
        ...

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        ...

    async def put_hint(self, hint: HintRecord) -> None:
        ...

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        ...

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        ...

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        ...

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        ...

    async def put_report(self, report: ReportRecord) -> None:
        ...

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        ...

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        ...

    async def append_outbox(self, record: OutboxRecord) -> None:
        ...

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        ...

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        ...

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        ...
