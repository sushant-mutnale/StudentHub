import asyncio
from typing import List, Optional, Tuple

from ..contracts.enums import InterviewType, Mode, SessionStatus
from ..contracts.messages import StartSessionCommand, StartSessionResult
from ..contracts.records import ConsentSnapshot, EventRecord, OutboxRecord, QuestionRecord, SessionRecord
from ..domain.behavioral_blueprint import build_behavioral_blueprint
from ..domain.session import Session, is_terminal_status
from ..errors import (
    DeviceConflict,
    InvalidState,
    NotOwner,
    SessionExists,
    SessionNotFound,
    UnsupportedInterviewType,
    UnsupportedMode,
    VersionConflict,
)
from ..ports.capabilities import QuestionRequest

_MAX_QUESTION_CHARS = 400


def _valid_question_text(text: Optional[str]) -> bool:
    if not text:
        return False
    stripped = text.strip()
    return 0 < len(stripped) <= _MAX_QUESTION_CHARS and stripped.endswith("?")


class InterviewEngine:
    def __init__(
        self,
        *,
        store,
        lease,
        clock,
        ids,
        analyzer,
        generator,
        evaluator,
        lease_ttl_seconds: int = 120,
        worker_id: str = "engine-worker",
        generation_timeout_seconds: float = 8.0,
    ):
        self.store = store
        self.lease = lease
        self.clock = clock
        self.ids = ids
        self.analyzer = analyzer
        self.generator = generator
        self.evaluator = evaluator
        self.lease_ttl_seconds = lease_ttl_seconds
        self.worker_id = worker_id
        self.generation_timeout_seconds = generation_timeout_seconds

    def _event(self, session: Session, event_type: str, payload: dict) -> EventRecord:
        return EventRecord(
            event_id=self.ids.new_id(),
            session_id=session.record.session_id,
            event_sequence=session.next_sequence(),
            event_type=event_type,
            payload=payload,
            created_at=self.clock.now(),
        )

    def _outbox(self, event_type: str, payload: dict) -> OutboxRecord:
        return OutboxRecord(
            outbox_id=self.ids.new_id(),
            event_type=event_type,
            payload=payload,
            created_at=self.clock.now(),
        )

    async def load_owned(self, session_id: str, candidate_id: str) -> SessionRecord:
        record = await self.store.load(session_id)
        if record is None:
            raise SessionNotFound()
        if record.candidate_id != candidate_id:
            raise NotOwner()
        return record

    def _validate_type_and_mode(self, interview_type: str, mode: str) -> None:
        if interview_type != InterviewType.BEHAVIORAL.value:
            raise UnsupportedInterviewType()
        if mode != Mode.PRACTICE.value:
            raise UnsupportedMode()

    async def start(self, cmd: StartSessionCommand) -> StartSessionResult:
        self._validate_type_and_mode(cmd.interview_type, cmd.mode)
        existing = await self.store.load_by_client_request_id(
            cmd.candidate_id, cmd.client_request_id
        )
        if existing is not None:
            question = await self.ensure_question(
                existing.session_id, self._first_question_request(existing)
            )
            fresh = await self.store.load(existing.session_id)
            return self._start_result(fresh or existing, question)

        active = await self.store.find_active(cmd.candidate_id, cmd.interview_type, cmd.mode)
        if active is not None:
            raise SessionExists(active.session_id)

        token = self.ids.new_token()
        session_id = self.ids.new_id()
        if not await self.lease.acquire(
            session_id, cmd.device_id, token, self.lease_ttl_seconds
        ):
            raise DeviceConflict()

        now = self.clock.now()
        blueprint = build_behavioral_blueprint(cmd.mode, cmd.role, cmd.job_description)
        record = SessionRecord(
            session_id=session_id,
            candidate_id=cmd.candidate_id,
            interview_type=cmd.interview_type,
            mode=cmd.mode,
            status=SessionStatus.PLANNED.value,
            version=0,
            event_sequence=1,
            last_applied_sequence=1,
            fencing_token=token,
            device_id=cmd.device_id,
            blueprint=blueprint,
            client_request_id=cmd.client_request_id,
            role=cmd.role,
            company=cmd.company,
            question_pending=True,
            consent=ConsentSnapshot(**(cmd.consent or {})),
            created_at=now,
            updated_at=now,
        )
        first_slot = blueprint.ordered_slots()[0]
        try:
            async with self.store.transaction():
                await self.store.insert(record)
                await self.store.append_event(
                    EventRecord(
                        event_id=self.ids.new_id(),
                        session_id=session_id,
                        event_sequence=1,
                        event_type="SessionCreated",
                        payload={"mode": cmd.mode, "interview_type": cmd.interview_type},
                        created_at=now,
                    )
                )
                await self.store.append_outbox(
                    self._outbox(
                        "interview_engine.question.requested",
                        {
                            "session_id": session_id,
                            "question_generation_key": f"{session_id}:0:first_question",
                            "purpose": "first_question",
                            "slot_id": first_slot.slot_id,
                            "session_version_at_request": 0,
                        },
                    )
                )
        except Exception:
            await self.lease.release(session_id, token)
            raise

        question = await self.ensure_question(
            session_id, self._first_question_request(record)
        )
        fresh = await self.store.load(session_id)
        return self._start_result(fresh, question)

    def _first_question_request(self, record: SessionRecord) -> dict:
        return {
            "slot_id": record.blueprint.ordered_slots()[0].slot_id,
            "purpose": "first_question",
            "session_version_at_request": 0,
            "question_generation_key": f"{record.session_id}:0:first_question",
        }

    def _start_result(
        self, record: SessionRecord, question: Optional[QuestionRecord]
    ) -> StartSessionResult:
        if question is None:
            raise InvalidState()
        return StartSessionResult(
            session_id=record.session_id,
            status=record.status,
            first_question=question.text,
            question_id=question.question_id,
            fencing_token=record.fencing_token,
            version=record.version,
            report_id=record.report_id,
            report_outcome=record.report_outcome,
            client_request_id=record.client_request_id,
        )

    def _request_value(self, request: dict, field: str) -> str:
        value = request.get(field)
        if not isinstance(value, str) or not value:
            raise InvalidState(f"question request is missing {field}")
        return value

    async def _generate_question(
        self, record: SessionRecord, slot, purpose: str, prior: List[str]
    ) -> Tuple[str, str]:
        try:
            generated = await asyncio.wait_for(
                self.generator.generate(
                    QuestionRequest(
                        session_id=record.session_id,
                        slot=slot,
                        purpose=purpose,
                        role=record.role,
                        company=record.company,
                        prior_questions=prior,
                    )
                ),
                timeout=self.generation_timeout_seconds,
            )
            text = getattr(generated, "text", None)
            source = getattr(generated, "source", "generated")
        except Exception:
            return slot.fallback_question, "fallback"
        if not _valid_question_text(text):
            return slot.fallback_question, "fallback"
        return text.strip(), source

    async def ensure_question(self, session_id: str, request: dict) -> Optional[QuestionRecord]:
        key = self._request_value(request, "question_generation_key")
        slot_id = self._request_value(request, "slot_id")
        purpose = self._request_value(request, "purpose")
        existing = await self.store.get_question_by_key(session_id, key)
        if existing is not None:
            return existing
        record = await self.store.load(session_id)
        if record is None:
            raise SessionNotFound()
        if is_terminal_status(record.status):
            return None
        slot = record.blueprint.slot(slot_id)
        prior = [turn.text for turn in await self.store.turns_for_session(session_id)]
        text, source = await self._generate_question(record, slot, purpose, prior)
        question = QuestionRecord(
            question_id=self.ids.new_id(),
            session_id=session_id,
            slot_id=slot.slot_id,
            question_generation_key=key,
            purpose=purpose,
            text=text,
            source=source,
            created_at=self.clock.now(),
        )
        async with self.store.transaction():
            current = await self.store.load(session_id)
            if current is None:
                raise SessionNotFound()
            if is_terminal_status(current.status):
                return None
            existing = await self.store.get_question_by_key(session_id, key)
            if existing is not None:
                return existing
            await self.store.put_question(question)
            session = Session.from_record(current)
            started = current.status == SessionStatus.PLANNED.value
            session.set_question(question.question_id, question.text, slot.slot_id, pending=False)
            session.record.pending_question_request = None
            session.bump()
            events = []
            if started:
                events.append(
                    self._event(session, "SessionStarted", {"slot_id": slot.slot_id})
                )
            events.append(
                self._event(
                    session,
                    "QuestionAsked",
                    {"question_id": question.question_id, "slot_id": slot.slot_id},
                )
            )
            if not await self.store.replace(session.to_record(), expected_version=current.version):
                existing = await self.store.get_question_by_key(session_id, key)
                if existing is not None:
                    return existing
                raise VersionConflict()
            for event in events:
                await self.store.append_event(event)
        return question
