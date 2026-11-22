import asyncio
from typing import List, Optional, Tuple

from ..contracts.enums import InterviewType, Mode, NextAction, SessionStatus
from ..contracts.messages import (
    SessionView,
    StartSessionCommand,
    StartSessionResult,
    SubmitTurnCommand,
    SubmitTurnResult,
)
from ..contracts.records import (
    ConsentSnapshot,
    EventRecord,
    EvidenceRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)
from ..domain.behavioral_blueprint import build_behavioral_blueprint
from ..domain.session import Session, is_terminal_status
from ..errors import (
    DeviceConflict,
    InvalidState,
    NotOwner,
    QuestionMismatch,
    QuestionPendingConflict,
    SessionExists,
    SessionNotFound,
    UnsupportedInterviewType,
    UnsupportedMode,
    VersionConflict,
)
from ..ports.capabilities import AnalysisRequest, QuestionRequest

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

    async def session_view(self, record: SessionRecord) -> SessionView:
        answered = await self.store.count_turns(record.session_id, kind="answer")
        return SessionView(
            session_id=record.session_id,
            status=record.status,
            version=record.version,
            question_pending=record.question_pending,
            outstanding_question=record.outstanding_question,
            question_id=record.current_question_id,
            report_id=record.report_id,
            report_outcome=record.report_outcome,
            fencing_token=record.fencing_token,
            hints_used=record.hint_count,
            hints_remaining=max(record.hint_budget - record.hint_count, 0),
            plan_position=record.plan_position,
            current_slot_id=record.current_slot_id,
            questions_answered=answered,
        )

    async def _assert_lease(
        self, record: SessionRecord, device_id: str, token: Optional[str]
    ) -> None:
        if record.device_id != device_id:
            raise DeviceConflict()
        if token is not None and token != record.fencing_token:
            raise DeviceConflict()
        if not await self.lease.confirm(record.session_id, device_id, record.fencing_token):
            raise DeviceConflict()

    async def _complete_pending_turn(
        self, cmd: SubmitTurnCommand, record: SessionRecord
    ) -> SubmitTurnResult:
        request = record.pending_question_request or {}
        if not request:
            raise InvalidState()
        question = await self.ensure_question(cmd.session_id, request)
        if question is None:
            raise InvalidState()
        fresh = await self.store.load(cmd.session_id)
        result = SubmitTurnResult(
            session_id=cmd.session_id,
            status=fresh.status,
            next_action="follow_up" if request.get("purpose") == "follow_up" else "next_slot",
            question=question.text,
            question_id=question.question_id,
            version=fresh.version,
        )
        async with self.store.transaction():
            await self.store.complete_turn_command(
                cmd.session_id, cmd.turn_idempotency_key, result.dict()
            )
        return result

    async def submit_turn(self, cmd: SubmitTurnCommand) -> SubmitTurnResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)

        existing = await self.store.get_turn_command(cmd.session_id, cmd.turn_idempotency_key)
        if existing is not None and existing.status == "complete":
            return SubmitTurnResult(**existing.result)
        if existing is not None and existing.status == "pending":
            return await self._complete_pending_turn(cmd, record)

        if is_terminal_status(record.status):
            raise InvalidState()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if record.question_pending:
            raise QuestionPendingConflict()
        if cmd.question_id is not None and cmd.question_id != record.current_question_id:
            raise QuestionMismatch()
        if cmd.expected_version is not None and cmd.expected_version != record.version:
            raise VersionConflict()

        session = Session.from_record(record)
        slot = session.slot()
        turn = TurnRecord(
            turn_id=self.ids.new_id(),
            session_id=record.session_id,
            sequence=await self.store.count_turns(record.session_id) + 1,
            kind=cmd.kind,
            question_id=record.current_question_id or "",
            slot_id=slot.slot_id,
            text=cmd.text,
            idempotency_key=cmd.turn_idempotency_key,
            device_id=cmd.device_id,
            created_at=self.clock.now(),
        )

        if cmd.kind == "clarification_request":
            reply = slot.clarification_text
            async with self.store.transaction():
                current = await self.store.load(cmd.session_id)
                if current is None:
                    raise SessionNotFound()
                current_session = Session.from_record(current)
                current_session.apply_clarification(turn, reply)
                await self.store.append_turn(turn)
                result = SubmitTurnResult(
                    session_id=cmd.session_id,
                    status=current_session.record.status,
                    next_action="await_answer",
                    question=current_session.record.outstanding_question,
                    question_id=current_session.record.current_question_id,
                    version=current_session.record.version,
                )
                await self.store.put_turn_command(
                    TurnCommandRecord(
                        session_id=cmd.session_id,
                        idempotency_key=cmd.turn_idempotency_key,
                        status="complete",
                        result=result.dict(),
                        created_at=self.clock.now(),
                        updated_at=self.clock.now(),
                    )
                )
                events = [
                    self._event(current_session, "TurnSubmitted", {"turn_id": turn.turn_id}),
                    self._event(
                        current_session,
                        "ClarificationReplied",
                        {"question_id": current_session.record.current_question_id},
                    ),
                ]
                if not await self.store.replace(
                    current_session.to_record(), expected_version=current.version
                ):
                    raise VersionConflict()
                for event in events:
                    await self.store.append_event(event)
            return result

        analysis = await self.analyzer.analyze(
            AnalysisRequest(
                session_id=record.session_id,
                turn_id=turn.turn_id,
                question_id=turn.question_id,
                slot_id=slot.slot_id,
                competency=slot.competency,
                text=cmd.text,
            )
        )
        evidence = None
        if analysis.instance == "new" and analysis.signal in ("sufficient", "incomplete"):
            evidence = EvidenceRecord(
                evidence_id=self.ids.new_id(),
                session_id=record.session_id,
                turn_id=turn.turn_id,
                question_id=turn.question_id,
                slot_id=slot.slot_id,
                competency=slot.competency,
                signal=analysis.signal,
                instance=analysis.instance,
                contradiction=analysis.contradiction,
                difficulty=slot.difficulty,
                created_at=self.clock.now(),
            )

        terminal = None
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            current_session = Session.from_record(current)
            if current_session.is_terminal():
                raise InvalidState()
            action = current_session.apply_answer(turn, analysis, evidence, slot.competency)
            await self.store.append_turn(turn)
            if evidence is not None:
                await self.store.append_evidence(evidence)
            events = [
                self._event(current_session, "TurnSubmitted", {"turn_id": turn.turn_id}),
                self._event(current_session, "TurnAnalysisRequested", {"turn_id": turn.turn_id}),
            ]
            if action == NextAction.END:
                report = ReportRecord(
                    report_id=current_session.record.report_id,
                    session_id=cmd.session_id,
                    outcome=current_session.record.report_outcome or "evaluating",
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
                await self.store.put_report(report)
                events.append(
                    self._event(
                        current_session, "SessionCompleted", {"report_id": report.report_id}
                    )
                )
                if report.outcome == "evaluating":
                    await self.store.append_outbox(
                        self._outbox(
                            "interview_engine.report.requested",
                            {"session_id": cmd.session_id, "report_id": report.report_id},
                        )
                    )
                terminal = SubmitTurnResult(
                    session_id=cmd.session_id,
                    status=current_session.record.status,
                    next_action="end",
                    report_id=current_session.record.report_id,
                    report_outcome=current_session.record.report_outcome,
                    version=current_session.record.version,
                )
                await self.store.put_turn_command(
                    TurnCommandRecord(
                        session_id=cmd.session_id,
                        idempotency_key=cmd.turn_idempotency_key,
                        status="complete",
                        result=terminal.dict(),
                        created_at=self.clock.now(),
                        updated_at=self.clock.now(),
                    )
                )
            else:
                await self.store.put_turn_command(
                    TurnCommandRecord(
                        session_id=cmd.session_id,
                        idempotency_key=cmd.turn_idempotency_key,
                        status="pending",
                        created_at=self.clock.now(),
                        updated_at=self.clock.now(),
                    )
                )
            if not await self.store.replace(
                current_session.to_record(), expected_version=current.version
            ):
                raise VersionConflict()
            for event in events:
                await self.store.append_event(event)

        if terminal is not None:
            return terminal

        request = current_session.record.pending_question_request or {}
        question = await self.ensure_question(cmd.session_id, request)
        if question is None:
            raise InvalidState()
        fresh = await self.store.load(cmd.session_id)
        result = SubmitTurnResult(
            session_id=cmd.session_id,
            status=fresh.status,
            next_action=action.value,
            question=question.text,
            question_id=question.question_id,
            version=fresh.version,
        )
        async with self.store.transaction():
            await self.store.complete_turn_command(
                cmd.session_id, cmd.turn_idempotency_key, result.dict()
            )
        return result
