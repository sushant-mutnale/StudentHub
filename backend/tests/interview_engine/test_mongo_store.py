from datetime import datetime

import pytest

from backend.interview_engine.adapters.mongo_store import MongoSessionStore
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.records import (
    EventRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    SessionRecord,
    TurnCommandRecord,
)
from backend.models.interview_engine_indexes import ensure_interview_engine_indexes
from tests.support.mongo_replica import start_replica_set

pytestmark = pytest.mark.integration

_COLLECTIONS = (
    "interview_engine_sessions",
    "interview_engine_events",
    "interview_engine_turns",
    "interview_engine_evidence",
    "interview_engine_questions",
    "interview_engine_hints",
    "interview_engine_turn_commands",
    "interview_engine_reports",
    "interview_engine_outbox",
)


def _slot():
    return BlueprintSlot(
        slot_id="s1", competency="c", dimension="c", difficulty="intermediate",
        intent="i", fallback_question="q", follow_up_question="f",
        clarification_text="c", hint_text="h",
    )


def _record(session_id="m1"):
    now = datetime.utcnow()
    return SessionRecord(
        session_id=session_id, candidate_id="c1", interview_type="behavioral", mode="practice",
        status="planned", version=0, event_sequence=0, last_applied_sequence=0,
        fencing_token="t1", device_id="d1",
        blueprint=Blueprint(groups=[BlueprintGroup(group_id="g", competency="c", slots=[_slot()])]),
        created_at=now, updated_at=now,
    )


def _question(session_id="m1", key="g1", text="first", question_id="q1"):
    return QuestionRecord(
        question_id=question_id, session_id=session_id, slot_id="s1",
        question_generation_key=key, purpose="ask", text=text, source="fallback",
        created_at=datetime.utcnow(),
    )


def _hint(session_id="m1", key="h1", text="hint one", hint_id="hint1"):
    return HintRecord(
        hint_id=hint_id, session_id=session_id, hint_idempotency_key=key,
        question_id="q1", text=text, created_at=datetime.utcnow(),
    )


def _command(session_id="m1", key="k1", status="pending"):
    now = datetime.utcnow()
    return TurnCommandRecord(
        session_id=session_id, idempotency_key=key, status=status,
        created_at=now, updated_at=now,
    )


def _outbox(outbox_id, event_type="interview_engine.session.created"):
    return OutboxRecord(
        outbox_id=outbox_id, event_type=event_type,
        payload={"session_id": "m1"}, created_at=datetime.utcnow(),
    )


async def _drop_engine_indexes(database) -> None:
    for name in _COLLECTIONS:
        try:
            for index in await database[name].list_indexes().to_list(length=None):
                if index["name"] != "_id_":
                    await database[name].drop_index(index["name"])
        except Exception:
            pass


@pytest.fixture
async def database():
    try:
        uri = start_replica_set()
    except RuntimeError as exc:
        pytest.skip(f"MongoDB replica set unavailable: {exc}")
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    db = client["interview_engine_replica_test"]
    for name in _COLLECTIONS:
        await db[name].delete_many({})
    await _drop_engine_indexes(db)
    yield db
    client.close()


@pytest.fixture
async def store(database):
    return MongoSessionStore(database, database.client)


async def test_transaction_commits_session_and_event_atomically(store):
    async with store.transaction():
        await store.insert(_record())
        await store.append_event(
            EventRecord(
                event_id="e1", session_id="m1", event_sequence=1,
                event_type="SessionCreated", payload={}, created_at=datetime.utcnow(),
            )
        )
    loaded = await store.load("m1")
    assert loaded is not None
    assert loaded.session_id == "m1"
    assert await store.count_turns("m1") == 0


async def test_transaction_rolls_back_session_and_event_together(store):
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.insert(_record())
            await store.append_event(
                EventRecord(
                    event_id="e2", session_id="m1", event_sequence=1,
                    event_type="SessionCreated", payload={}, created_at=datetime.utcnow(),
                )
            )
            raise RuntimeError("boom")
    assert await store.load("m1") is None
    collection = store._db["interview_engine_events"]
    assert await collection.count_documents({"session_id": "m1"}) == 0


async def test_nested_transaction_is_rejected(store):
    async with store.transaction():
        with pytest.raises(RuntimeError):
            async with store.transaction():
                pass
    assert store._session.get() is None


async def test_outbox_writers_join_ambient_transaction(store):
    await store.append_outbox(_outbox("o1"))
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.mark_outbox_failed("o1", "boom")
            raise RuntimeError("boom")
    doc = await store._db["interview_engine_outbox"].find_one({"outbox_id": "o1"})
    assert doc["status"] == "pending"
    assert doc.get("last_error") is None
    assert await store.outbox_errors() == {}


async def test_optimistic_replace(store):
    async with store.transaction():
        await store.insert(_record())
    loaded = await store.load("m1")
    loaded.version = 1
    assert await store.replace(loaded, expected_version=0) is True
    assert await store.replace(loaded, expected_version=0) is False


async def test_question_put_is_first_writer_wins(store):
    await store.put_question(_question(text="first"))
    await store.put_question(_question(text="second", question_id="q2"))
    stored = await store.get_question_by_key("m1", "g1")
    assert stored is not None
    assert stored.text == "first"
    assert stored.question_id == "q1"


async def test_question_keys_are_session_scoped(store):
    await store.put_question(_question(session_id="m1", text="one"))
    await store.put_question(_question(session_id="m2", text="two", question_id="q2"))
    first = await store.get_question_by_key("m1", "g1")
    second = await store.get_question_by_key("m2", "g1")
    assert first.text == "one"
    assert second.text == "two"


async def test_hint_keys_are_session_scoped(store):
    await store.put_hint(_hint(session_id="m1", text="one"))
    await store.put_hint(_hint(session_id="m2", text="two", hint_id="hint2"))
    first = await store.get_hint_by_key("m1", "h1")
    second = await store.get_hint_by_key("m2", "h1")
    assert first.text == "one"
    assert second.text == "two"


async def test_complete_turn_command_does_not_overwrite_a_complete_record(store):
    await store.put_turn_command(_command())
    await store.complete_turn_command("m1", "k1", {"answer": "a"})
    await store.complete_turn_command("m1", "k1", {"answer": "b"})
    command = await store.get_turn_command("m1", "k1")
    assert command.status == "complete"
    assert command.result == {"answer": "a"}


async def test_outbox_claim_skips_foreign_event_types(store):
    await store.append_outbox(_outbox("o-legacy", event_type="outbox_events.legacy"))
    await store.append_outbox(_outbox("o-engine", event_type="interview_engine.report.requested"))
    claimed = await store.claim_outbox("w1", 5)
    assert [c.event_type for c in claimed] == ["interview_engine.report.requested"]
    legacy = await store._db["interview_engine_outbox"].find_one(
        {"event_type": "outbox_events.legacy"}
    )
    assert legacy["status"] == "pending"


async def test_outbox_attempt_budget_stops_claiming(store):
    await store.append_outbox(_outbox("o-engine"))
    for _ in range(10):
        claimed = await store.claim_outbox("w1", 1)
        if not claimed:
            break
        await store.mark_outbox_failed(claimed[0].outbox_id, "boom")
    else:
        pytest.fail("claim_outbox never stopped claiming")
    assert await store.claim_outbox("w1", 1) == []
    errors = await store.outbox_errors()
    assert errors


async def test_ensure_interview_engine_indexes_creates_them(database):
    await ensure_interview_engine_indexes(database)
    indexes = await database.interview_engine_questions.list_indexes().to_list(length=None)
    keys = {tuple(i["key"]) for i in indexes}
    assert ("session_id", "question_generation_key") in keys
    unique = next(i for i in indexes if tuple(i["key"]) == ("session_id", "question_generation_key"))
    assert unique["unique"] is True

    hint_indexes = await database.interview_engine_hints.list_indexes().to_list(length=None)
    hint_keys = {tuple(i["key"]) for i in hint_indexes}
    assert ("session_id", "hint_idempotency_key") in hint_keys
    hint_unique = next(
        i for i in hint_indexes if tuple(i["key"]) == ("session_id", "hint_idempotency_key")
    )
    assert hint_unique["unique"] is True

    outbox_indexes = await database.interview_engine_outbox.list_indexes().to_list(length=None)
    outbox_keys = {tuple(i["key"]) for i in outbox_indexes}
    assert ("status", "created_at") in outbox_keys
    outbox_id = next(i for i in outbox_indexes if tuple(i["key"]) == ("outbox_id",))
    assert outbox_id["unique"] is True

    legacy = await database.outbox_events.list_indexes().to_list(length=None)
    assert [i["name"] for i in legacy] == [] or all(i["name"] == "_id_" for i in legacy)
