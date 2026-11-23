import asyncio
from typing import List, Optional, Tuple

from ..contracts.enums import InterviewType, Mode, NextAction, SessionStatus
from ..contracts.messages import (
    EndSessionCommand,
    EndSessionResult,
    HintResult,
    PauseSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    ResumeSessionResult,
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
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)
from ..domain.behavioral_blueprint import build_behavioral_blueprint
from ..domain.scoring import InstanceFact, confidence_for, counts_for_scoring, level_for
from ..domain.session import Session, is_terminal_status
from ..errors import (
    CommandIdRequired,
    DeviceConflict,
    HintLimitReached,
    HintUnavailable,
    InvalidState,
    NoReport,
    NotOwner,
    PauseLimitReached,
    QuestionMismatch,
    QuestionPendingConflict,
    QuestionSuperseded,
    SessionExists,
    SessionNotFound,
    UnsupportedInterviewType,
    UnsupportedMode,
    VersionConflict,
)
from ..ports.capabilities import (
    AnalysisRequest,
    CompetencyEvaluationInput,
    EvaluationRequest,
    QuestionRequest,
)
from .report_builder import build_report

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
        report_max_attempts: int = 5,
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
        self.report_max_attempts = report_max_attempts

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
        if is_terminal_status(record.status):
            return SubmitTurnResult(
                session_id=cmd.session_id,
                status=record.status,
                next_action="end",
                report_id=record.report_id,
                report_outcome=record.report_outcome,
                version=record.version,
            )
        request = record.pending_question_request or {}
        if request:
            question = await self.ensure_question(cmd.session_id, request)
            purpose = request.get("purpose", "next_question")
        else:
            question = await self._outstanding_question(cmd.session_id, record)
            purpose = question.purpose if question is not None else "next_question"
        if question is None:
            raise InvalidState()
        fresh = await self.store.load(cmd.session_id) or record
        result = SubmitTurnResult(
            session_id=cmd.session_id,
            status=fresh.status,
            next_action="follow_up" if purpose == "follow_up" else "next_slot",
            question=question.text,
            question_id=question.question_id,
            version=fresh.version,
        )
        async with self.store.transaction():
            await self.store.complete_turn_command(
                cmd.session_id, cmd.turn_idempotency_key, result.dict()
            )
        return result

    async def _outstanding_question(
        self, session_id: str, record: SessionRecord
    ) -> Optional[QuestionRecord]:
        if is_terminal_status(record.status) or not record.current_question_id:
            return None
        for question in await self.store.questions_for_session(session_id):
            if question.question_id == record.current_question_id:
                return question
        return None

    async def submit_turn(self, cmd: SubmitTurnCommand) -> SubmitTurnResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)

        existing = await self.store.get_turn_command(cmd.session_id, cmd.turn_idempotency_key)
        if existing is not None:
            record = await self.store.load(cmd.session_id) or record
            if existing.status == "complete":
                return SubmitTurnResult(**existing.result)
            if existing.status == "pending":
                return await self._complete_pending_turn(cmd, record)

        if is_terminal_status(record.status):
            raise InvalidState()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if record.question_pending:
            raise QuestionPendingConflict()
        if cmd.expected_version is not None and cmd.expected_version != record.version:
            raise VersionConflict()
        if cmd.question_id is not None and cmd.question_id != record.current_question_id:
            raise QuestionMismatch()

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
            turn = turn.copy(update={"reply": reply})
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
                    reply=reply,
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
                        {
                            "question_id": current_session.record.current_question_id,
                            "reply": reply,
                        },
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
                if current_session.record.report_outcome is None:
                    raise InvalidState()
                report = ReportRecord(
                    report_id=current_session.record.report_id,
                    session_id=cmd.session_id,
                    outcome=current_session.record.report_outcome,
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
                await self.store.put_report(report)
                events.append(
                    self._event(
                        current_session,
                        "SessionCompleted",
                        {
                            "report_id": report.report_id,
                            "reason": "candidate_completed",
                        },
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

    async def request_hint(self, cmd: RequestHintCommand) -> HintResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        if record.mode != Mode.PRACTICE.value:
            raise HintUnavailable()
        existing = await self.store.get_hint_by_key(
            cmd.session_id, cmd.hint_idempotency_key
        )
        if existing is not None:
            fresh = await self.store.load(cmd.session_id) or record
            return HintResult(
                hint=existing.text,
                hints_used=existing.hints_used,
                remaining=max(fresh.hint_budget - existing.hints_used, 0),
                version=fresh.version,
                question_id=existing.question_id,
            )
        if record.question_pending:
            raise QuestionPendingConflict()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if cmd.question_id is not None and cmd.question_id != record.current_question_id:
            raise QuestionSuperseded()
        if record.hint_count >= record.hint_budget:
            raise HintLimitReached()
        if not record.current_slot_id:
            raise InvalidState()
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            if current.hint_count >= current.hint_budget:
                raise HintLimitReached()
            existing = await self.store.get_hint_by_key(
                cmd.session_id, cmd.hint_idempotency_key
            )
            if existing is not None:
                return HintResult(
                    hint=existing.text,
                    hints_used=existing.hints_used,
                    remaining=max(current.hint_budget - existing.hints_used, 0),
                    version=current.version,
                    question_id=existing.question_id,
                )
            hint = HintRecord(
                hint_id=self.ids.new_id(),
                session_id=current.session_id,
                hint_idempotency_key=cmd.hint_idempotency_key,
                question_id=current.current_question_id or "",
                text=current.blueprint.slot(current.current_slot_id).hint_text,
                hints_used=current.hint_count + 1,
                created_at=self.clock.now(),
            )
            session = Session.from_record(current)
            session.record.hint_count += 1
            session.bump()
            event = self._event(
                session,
                "HintProvided",
                {"question_id": hint.question_id, "hints_used": hint.hints_used},
            )
            await self.store.put_hint(hint)
            if not await self.store.replace(
                session.to_record(), expected_version=current.version
            ):
                raise VersionConflict()
            await self.store.append_event(event)
        return HintResult(
            hint=hint.text,
            hints_used=hint.hints_used,
            remaining=max(session.record.hint_budget - hint.hints_used, 0),
            version=session.record.version,
            question_id=hint.question_id,
        )

    async def pause(self, cmd: PauseSessionCommand) -> SessionView:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        existing = await self.store.get_turn_command(
            cmd.session_id, f"pause:{cmd.command_id}"
        )
        if existing is not None and existing.status == "complete":
            return SessionView(**existing.result)
        if record.question_pending:
            raise QuestionPendingConflict()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if record.mode == Mode.FORMAL.value and record.pause_count >= 1:
            raise PauseLimitReached()
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            session = Session.from_record(current)
            session.mark_paused()
            event = self._event(session, "SessionPaused", {"reason": cmd.reason})
            if not await self.store.replace(
                session.to_record(), expected_version=current.version
            ):
                raise VersionConflict()
            await self.store.append_event(event)
        view = await self.session_view(session.to_record())
        async with self.store.transaction():
            await self.store.put_turn_command(
                TurnCommandRecord(
                    session_id=cmd.session_id,
                    idempotency_key=f"pause:{cmd.command_id}",
                    status="complete",
                    result=view.dict(),
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
            )
        return view

    async def resume(self, cmd: ResumeSessionCommand) -> ResumeSessionResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        if is_terminal_status(record.status):
            raise InvalidState()
        paused = record.status == SessionStatus.PAUSED.value
        if paused and not cmd.command_id:
            raise CommandIdRequired()
        if cmd.command_id:
            existing = await self.store.get_turn_command(
                cmd.session_id, f"resume:{cmd.command_id}"
            )
            if existing is not None and existing.status == "complete":
                return ResumeSessionResult(**existing.result)
        token = self.ids.new_token()
        await self.lease.takeover(
            cmd.session_id, cmd.device_id, token, self.lease_ttl_seconds
        )
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            if current.device_id != cmd.device_id:
                current.disconnect_count += 1
            current.device_id = cmd.device_id
            current.fencing_token = token
            current.updated_at = self.clock.now()
            events = []
            if current.status == SessionStatus.PAUSED.value:
                session = Session.from_record(current)
                session.mark_resumed()
                current = session.to_record()
                events.append(
                    EventRecord(
                        event_id=self.ids.new_id(),
                        session_id=cmd.session_id,
                        event_sequence=current.event_sequence + 1,
                        event_type="SessionResumed",
                        payload={"command_id": cmd.command_id},
                        created_at=self.clock.now(),
                    )
                )
                current.event_sequence += 1
                current.last_applied_sequence = current.event_sequence
            events.append(
                EventRecord(
                    event_id=self.ids.new_id(),
                    session_id=cmd.session_id,
                    event_sequence=current.event_sequence + 1,
                    event_type="SessionLeaseTakenOver",
                    payload={"device_id": cmd.device_id},
                    created_at=self.clock.now(),
                )
            )
            current.event_sequence += 1
            current.last_applied_sequence = current.event_sequence
            if not await self.store.replace(current, expected_version=record.version):
                raise VersionConflict()
            for event in events:
                await self.store.append_event(event)
        if current.question_pending and current.pending_question_request:
            await self.ensure_question(cmd.session_id, current.pending_question_request)
            current = await self.store.load(cmd.session_id) or current
        result = ResumeSessionResult(
            session_id=current.session_id,
            status=current.status,
            fencing_token=current.fencing_token,
            question=current.outstanding_question,
            question_id=current.current_question_id,
            version=current.version,
            question_pending=current.question_pending,
        )
        if paused and cmd.command_id:
            async with self.store.transaction():
                await self.store.put_turn_command(
                    TurnCommandRecord(
                        session_id=cmd.session_id,
                        idempotency_key=f"resume:{cmd.command_id}",
                        status="complete",
                        result=result.dict(),
                        created_at=self.clock.now(),
                        updated_at=self.clock.now(),
                    )
                )
        return result

    async def end(self, cmd: EndSessionCommand) -> EndSessionResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        if is_terminal_status(record.status):
            return EndSessionResult(
                session_id=record.session_id,
                status=record.status,
                report_id=record.report_id,
                report_outcome=record.report_outcome,
            )
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            session = Session.from_record(current)
            report_id = current.report_id or self.ids.new_id()
            outcome = "suppressed" if not current.consent.evaluation else "evaluating"
            session.begin_completion(report_id, outcome)
            await self.store.put_report(
                ReportRecord(
                    report_id=report_id,
                    session_id=current.session_id,
                    outcome=outcome,
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
            )
            event = self._event(
                session,
                "SessionCompleted",
                {"report_id": report_id, "reason": cmd.reason},
            )
            if not await self.store.replace(
                session.to_record(), expected_version=current.version
            ):
                raise VersionConflict()
            await self.store.append_event(event)
            result = EndSessionResult(
                session_id=session.record.session_id,
                status=session.record.status,
                report_id=session.record.report_id,
                report_outcome=session.record.report_outcome,
            )
            await self.store.put_turn_command(
                TurnCommandRecord(
                    session_id=cmd.session_id,
                    idempotency_key=f"end:{cmd.end_command_id}",
                    status="complete",
                    result=result.dict(),
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
            )
            terminal = SubmitTurnResult(
                session_id=current.session_id,
                status=session.record.status,
                next_action="end",
                report_id=session.record.report_id,
                report_outcome=session.record.report_outcome,
                version=session.record.version,
            )
            for command in await self.store.turn_commands_for_session(cmd.session_id):
                if command.status == "pending":
                    await self.store.complete_turn_command(
                        cmd.session_id, command.idempotency_key, terminal.dict()
                    )
            if outcome == "evaluating":
                await self.store.append_outbox(
                    self._outbox(
                        "interview_engine.report.requested",
                        {"session_id": current.session_id, "report_id": report_id},
                    )
                )
        return result

    async def get_report(
        self, candidate_id: str, report_id: Optional[str]
    ) -> ReportRecord:
        if not report_id:
            raise NoReport()
        report = await self.store.get_report(report_id)
        if report is None:
            raise NoReport()
        record = await self.store.load(report.session_id)
        if record is None:
            raise NoReport()
        if record.candidate_id != candidate_id:
            raise NotOwner()
        return report

    async def build_report_body(self, report_id: str) -> Optional[dict]:
        report = await self.store.get_report(report_id)
        if report is None:
            return None
        record = await self.store.load(report.session_id)
        if record is None:
            return None
        evidence = await self.store.evidence_for_session(record.session_id)
        turns = await self.store.turns_for_session(record.session_id)
        inputs = []
        for group in record.blueprint.groups:
            items = [item for item in evidence if item.competency == group.competency]
            facts = [
                InstanceFact(
                    competency=item.competency,
                    question_id=item.question_id,
                    signal=item.signal,
                    contradiction=item.contradiction,
                )
                for item in items
                if counts_for_scoring(item.signal, item.instance)
            ]
            inputs.append(
                CompetencyEvaluationInput(
                    competency=group.competency,
                    level=level_for(facts).value,
                    confidence=confidence_for(facts).value,
                    instances=len(facts),
                )
            )
        output = await self.evaluator.evaluate(
            EvaluationRequest(
                session_id=record.session_id,
                report_id=report_id,
                role=record.role,
                company=record.company,
                competencies=inputs,
            )
        )
        body = build_report(record, evidence, turns, output)
        return body.dict()

    async def drain_outbox(self, limit: int = 10) -> int:
        claimed = await self.store.claim_outbox(self.worker_id, limit)
        processed = 0
        for item in claimed:
            try:
                handler = self._outbox_handlers().get(item.event_type)
                if handler is None:
                    raise InvalidState(f"no handler for {item.event_type}")
                await handler(item.payload)
                await self.store.mark_outbox_processed(item.outbox_id)
                processed += 1
            except Exception as exc:
                await self.store.mark_outbox_failed(item.outbox_id, str(exc))
        return processed

    def _outbox_handlers(self) -> dict:
        return {
            "interview_engine.report.requested": self._handle_report_requested,
            "interview_engine.question.requested": self._handle_question_requested,
        }

    async def _handle_question_requested(self, payload: dict) -> None:
        session_id = self._request_value(payload, "session_id")
        request = {
            "slot_id": self._request_value(payload, "slot_id"),
            "purpose": self._request_value(payload, "purpose"),
            "session_version_at_request": payload.get("session_version_at_request", 0),
            "question_generation_key": self._request_value(payload, "question_generation_key"),
        }
        await self.ensure_question(session_id, request)

    async def _handle_report_requested(self, payload: dict) -> None:
        report_id = payload["report_id"]
        report = await self.store.get_report(report_id)
        if report is None or report.outcome != "evaluating":
            return
        try:
            body = await self.build_report_body(report_id)
            if body is None:
                raise InvalidState("report body could not be assembled")
        except Exception:
            report.attempts += 1
            report.updated_at = self.clock.now()
            if report.attempts >= self.report_max_attempts:
                report.outcome = "failed"
            await self.store.update_report(report, expected_outcome="evaluating")
            raise
        report.outcome = "ready"
        report.body = body
        report.attempts += 1
        report.updated_at = self.clock.now()
        if not await self.store.update_report(report, expected_outcome="evaluating"):
            raise VersionConflict()
        record = await self.store.load(report.session_id)
        if record is not None and record.report_outcome == "evaluating":
            async with self.store.transaction():
                current = await self.store.load(report.session_id)
                current.report_outcome = "ready"
                current.updated_at = self.clock.now()
                await self.store.replace(current, expected_version=current.version)

