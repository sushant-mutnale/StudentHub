from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import List, Optional

from pymongo import ReturnDocument

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

_SESSIONS = "interview_engine_sessions"
_EVENTS = "interview_engine_events"
_TURNS = "interview_engine_turns"
_EVIDENCE = "interview_engine_evidence"
_QUESTIONS = "interview_engine_questions"
_HINTS = "interview_engine_hints"
_COMMANDS = "interview_engine_turn_commands"
_REPORTS = "interview_engine_reports"
_OUTBOX = "interview_engine_outbox"

_ACTIVE = (
    "planned",
    "in_progress",
    "paused",
)

_OUTBOX_PREFIX = "^interview_engine\\."


class MongoSessionStore:
    max_attempts = 5

    def __init__(self, database, client):
        self._db = database
        self._client = client
        self._session: ContextVar = ContextVar("interview_engine_mongo_session", default=None)

    def _opts(self) -> dict:
        active = self._session.get()
        return {"session": active} if active is not None else {}

    @asynccontextmanager
    async def transaction(self):
        async with await self._client.start_session() as mongo_session:
            token = self._session.set(mongo_session)
            mongo_session.start_transaction()
            try:
                yield self
                await mongo_session.commit_transaction()
            except Exception:
                if mongo_session.in_transaction:
                    await mongo_session.abort_transaction()
                raise
            finally:
                self._session.reset(token)

    def _command_id(self, session_id: str, key: str) -> str:
        return f"{session_id}:{key}"

    def _question_id(self, session_id: str, key: str) -> str:
        return f"{session_id}:{key}"

    def _hint_id(self, session_id: str, key: str) -> str:
        return f"{session_id}:{key}"

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        doc = await self._db[_SESSIONS].find_one({"_id": session_id}, **self._opts())
        return SessionRecord.parse_obj(doc) if doc else None

    async def load_by_client_request_id(
        self, candidate_id: str, client_request_id: str
    ) -> Optional[SessionRecord]:
        doc = await self._db[_SESSIONS].find_one(
            {"candidate_id": candidate_id, "client_request_id": client_request_id},
            **self._opts(),
        )
        return SessionRecord.parse_obj(doc) if doc else None

    async def find_active(
        self, candidate_id: str, interview_type: str, mode: str
    ) -> Optional[SessionRecord]:
        doc = await self._db[_SESSIONS].find_one(
            {
                "candidate_id": candidate_id,
                "interview_type": interview_type,
                "mode": mode,
                "status": {"$in": list(_ACTIVE)},
            },
            **self._opts(),
        )
        return SessionRecord.parse_obj(doc) if doc else None

    async def insert(self, record: SessionRecord) -> None:
        doc = record.dict()
        doc["_id"] = record.session_id
        await self._db[_SESSIONS].insert_one(doc, **self._opts())

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        doc = record.dict()
        doc.pop("session_id", None)
        result = await self._db[_SESSIONS].update_one(
            {"_id": record.session_id, "version": expected_version},
            {"$set": doc},
            **self._opts(),
        )
        return result.matched_count == 1

    async def append_event(self, event: EventRecord) -> None:
        doc = event.dict()
        doc["_id"] = event.event_id
        await self._db[_EVENTS].insert_one(doc, **self._opts())

    async def append_turn(self, turn: TurnRecord) -> None:
        doc = turn.dict()
        doc["_id"] = turn.turn_id
        await self._db[_TURNS].insert_one(doc, **self._opts())

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        query = {"session_id": session_id}
        if kind is not None:
            query["kind"] = kind
        return await self._db[_TURNS].count_documents(query, **self._opts())

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        cursor = self._db[_TURNS].find({"session_id": session_id}, **self._opts()).sort(
            "sequence", 1
        )
        return [TurnRecord.parse_obj(doc) async for doc in cursor]

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        doc = evidence.dict()
        doc["_id"] = evidence.evidence_id
        await self._db[_EVIDENCE].insert_one(doc, **self._opts())

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        cursor = self._db[_EVIDENCE].find({"session_id": session_id}, **self._opts())
        return [EvidenceRecord.parse_obj(doc) async for doc in cursor]

    async def put_question(self, question: QuestionRecord) -> None:
        doc = question.dict()
        doc["_id"] = self._question_id(question.session_id, question.question_generation_key)
        await self._db[_QUESTIONS].update_one(
            {"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True, **self._opts()
        )

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        doc = await self._db[_QUESTIONS].find_one(
            {"_id": self._question_id(session_id, key)}, **self._opts()
        )
        if doc and doc.get("session_id") == session_id:
            return QuestionRecord.parse_obj(doc)
        return None

    async def questions_for_session(self, session_id: str) -> List[QuestionRecord]:
        cursor = self._db[_QUESTIONS].find({"session_id": session_id}, **self._opts())
        return [QuestionRecord.parse_obj(doc) async for doc in cursor]

    async def put_hint(self, hint: HintRecord) -> None:
        doc = hint.dict()
        doc["_id"] = self._hint_id(hint.session_id, hint.hint_idempotency_key)
        await self._db[_HINTS].update_one(
            {"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True, **self._opts()
        )

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        doc = await self._db[_HINTS].find_one(
            {"_id": self._hint_id(session_id, key)}, **self._opts()
        )
        if doc and doc.get("session_id") == session_id:
            return HintRecord.parse_obj(doc)
        return None

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        doc = await self._db[_COMMANDS].find_one(
            {"_id": self._command_id(session_id, key)}, **self._opts()
        )
        if doc and doc.get("session_id") == session_id:
            return TurnCommandRecord.parse_obj(doc)
        return None

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        doc = command.dict()
        doc["_id"] = self._command_id(command.session_id, command.idempotency_key)
        await self._db[_COMMANDS].insert_one(doc, **self._opts())

    async def turn_commands_for_session(self, session_id: str) -> List[TurnCommandRecord]:
        cursor = self._db[_COMMANDS].find({"session_id": session_id}, **self._opts())
        return [TurnCommandRecord.parse_obj(doc) async for doc in cursor]

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        await self._db[_COMMANDS].update_one(
            {"_id": self._command_id(session_id, key), "status": "pending"},
            {"$set": {"status": "complete", "result": result}},
            **self._opts(),
        )

    async def put_report(self, report: ReportRecord) -> None:
        doc = report.dict()
        doc["_id"] = report.report_id
        await self._db[_REPORTS].insert_one(doc, **self._opts())

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        doc = await self._db[_REPORTS].find_one({"_id": report_id}, **self._opts())
        return ReportRecord.parse_obj(doc) if doc else None

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        doc = report.dict()
        doc.pop("report_id", None)
        result = await self._db[_REPORTS].update_one(
            {"_id": report.report_id, "outcome": expected_outcome},
            {"$set": doc},
            **self._opts(),
        )
        return result.matched_count == 1

    async def append_outbox(self, record: OutboxRecord) -> None:
        doc = record.dict()
        doc["_id"] = record.outbox_id
        doc["status"] = "pending"
        doc["attempts"] = 0
        await self._db[_OUTBOX].insert_one(doc, **self._opts())

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        claimed = []
        for _ in range(limit):
            doc = await self._db[_OUTBOX].find_one_and_update(
                {
                    "status": {"$in": ["pending", "failed"]},
                    "attempts": {"$lt": self.max_attempts},
                    "event_type": {"$regex": _OUTBOX_PREFIX},
                },
                {
                    "$set": {"status": "processing", "worker_id": worker_id},
                    "$inc": {"attempts": 1},
                },
                sort=[("created_at", 1)],
                return_document=ReturnDocument.AFTER,
                **self._opts(),
            )
            if doc is None:
                break
            doc.pop("_id", None)
            claimed.append(OutboxRecord.parse_obj(doc))
        return claimed

    async def outbox_errors(self) -> dict:
        cursor = self._db[_OUTBOX].find(
            {"status": "failed", "last_error": {"$ne": None}},
            {"_id": 0, "outbox_id": 1, "last_error": 1},
        )
        return {doc["outbox_id"]: doc["last_error"] async for doc in cursor}

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        await self._db[_OUTBOX].update_one(
            {"_id": outbox_id},
            {"$set": {"status": "processed", "processed_at": datetime.utcnow()}},
        )

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        await self._db[_OUTBOX].update_one(
            {"_id": outbox_id},
            {"$set": {"status": "failed", "last_error": error}},
        )
