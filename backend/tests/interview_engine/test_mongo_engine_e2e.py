import pytest

from backend.interview_engine.adapters.mongo_store import MongoSessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand

pytestmark = pytest.mark.integration


@pytest.fixture
def mongo_engine():
    from tests.support.mongo_replica import start_replica_set
    from motor.motor_asyncio import AsyncIOMotorClient

    try:
        uri = start_replica_set()
    except Exception as exc:
        pytest.skip(f"replica set unavailable: {exc}")
    client = AsyncIOMotorClient(uri)
    database = client["interview_engine_e2e"]
    engine = InterviewEngine(
        store=MongoSessionStore(database, client),
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=HeuristicAnalyzer(),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    yield engine, database
    client.close()


@pytest.mark.asyncio
async def test_start_persists_session_and_outbox_atomically(mongo_engine):
    engine, database = mongo_engine
    await database.interview_engine_sessions.delete_many({})
    await database.interview_engine_outbox.delete_many({})
    await database.interview_engine_events.delete_many({})
    result = await engine.start(StartSessionCommand(
        candidate_id="c1", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-1", role="Senior Engineer",
    ))
    session = await database.interview_engine_sessions.find_one({"_id": result.session_id})
    assert session["status"] == "in_progress"
    assert session["version"] == 1
    outbox = await database.interview_engine_outbox.find_one(
        {"event_type": "interview_engine.question.requested"}
    )
    assert outbox is not None
    events = [e async for e in database.interview_engine_events.find({"session_id": result.session_id})]
    assert [e["event_type"] for e in events] == [
        "SessionCreated",
        "SessionStarted",
        "QuestionAsked",
    ]


@pytest.mark.asyncio
async def test_duplicate_start_returns_same_session(mongo_engine):
    engine, database = mongo_engine
    await database.interview_engine_sessions.delete_many({})
    await database.interview_engine_events.delete_many({})
    first = await engine.start(StartSessionCommand(
        candidate_id="c2", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-9",
    ))
    second = await engine.start(StartSessionCommand(
        candidate_id="c2", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-9",
    ))
    assert first.session_id == second.session_id
    assert await database.interview_engine_sessions.count_documents({"candidate_id": "c2"}) == 1
