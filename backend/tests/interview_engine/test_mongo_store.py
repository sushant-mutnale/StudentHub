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
    yield db
    client.close()


@pytest.fixture
async def store(database):
    return MongoSessionStore(database, database.client)


async def test_transaction_commits_session_and_event_atomically(store, database):
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
    assert await database["interview_engine_events"].count_documents({"session_id": "m1"}) == 1


async def test_transaction_rolls_back_on_error(store, database):
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.insert(_record())
            raise RuntimeError("boom")
    assert await store.load("m1") is None
    assert await database["interview_engine_sessions"].count_documents({}) == 0


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
    await store.append_outbox(_outbox("o-engine"))
    claimed = await store.claim_outbox("worker-1", limit=10)
    assert [record.outbox_id for record in claimed] == ["o-engine"]


async def test_outbox_attempt_budget_stops_claiming(store):
    await store.append_outbox(_outbox("o-engine"))
    claims = 0
    while True:
        claimed = await store.claim_outbox("worker-1", limit=1)
        if not claimed:
            break
        claims += 1
        await store.mark_outbox_failed(claimed[0].outbox_id, "boom")
    assert claims == store.max_attempts
    assert (await store.outbox_errors())["o-engine"] == "boom"


async def test_ensure_interview_engine_indexes_creates_them(database):
    async def unique_indexes(collection):
        info = await database[collection].index_information()
        return {name for name, spec in info.items() if spec.get("unique")}

    await ensure_interview_engine_indexes(database)
    assert "candidate_id_1_client_request_id_1" in await unique_indexes(
        "interview_engine_sessions"
    )
    assert "session_id_1_event_sequence_1" in await unique_indexes("interview_engine_events")
    assert await unique_indexes("interview_engine_turns") >= {
        "session_id_1_sequence_1",
        "session_id_1_idempotency_key_1",
    }
    assert "session_id_1_idempotency_key_1" in await unique_indexes(
        "interview_engine_turn_commands"
    )
    assert "outbox_id_1" in await unique_indexes("interview_engine_outbox")
