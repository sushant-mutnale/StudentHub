import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient

from backend.interview_engine.adapters.mongo_store import MongoSessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import (
    InMemoryLease,
    SystemClock,
    UuidIds,
)
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand

_DB_NAME = "studenthub_compose_smoke"


async def run(client):
    database = client[_DB_NAME]
    engine = InterviewEngine(
        store=MongoSessionStore(database, client),
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=HeuristicAnalyzer(),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    result = await engine.start(
        StartSessionCommand(
            candidate_id="compose-smoke",
            interview_type="behavioral",
            mode="practice",
            device_id="compose-smoke-device",
            client_request_id="compose-smoke-request",
            role="Senior Engineer",
        )
    )
    session = await database.interview_engine_sessions.find_one(
        {"_id": result.session_id}
    )
    outbox = await database.interview_engine_outbox.find_one(
        {"event_type": "interview_engine.question.requested"}
    )
    events = [
        event["event_type"]
        async for event in database.interview_engine_events.find(
            {"session_id": result.session_id}
        )
    ]
    if session is None or session.get("status") != "in_progress":
        raise RuntimeError("engine start did not persist a session")
    if outbox is None:
        raise RuntimeError("engine start did not persist an outbox event")
    if events != ["SessionCreated", "SessionStarted", "QuestionAsked"]:
        raise RuntimeError("engine start did not persist the expected events")
    return result.session_id


async def main():
    client = AsyncIOMotorClient(
        os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000
    )
    try:
        await run(client)
    finally:
        await client.drop_database(_DB_NAME)
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
