import pytest

from backend.interview_engine.adapters.factory import build_engine
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease
from backend.interview_engine.compatibility.dependencies import get_engine
from backend.main import app


@pytest.fixture
def engine():
    instance = build_engine(
        store=InMemorySessionStore(),
        lease=InMemoryLease(),
        analyzer=ScriptedAnalyzer([]),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    app.dependency_overrides[get_engine] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_engine, None)


@pytest.mark.asyncio
async def test_practice_session_from_start_to_ready_report(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Senior Engineer", "company": "Acme", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    session = start.json()
    for index in range(10):
        answer = await client.post(
            "/agent-interview/answer",
            json={
                "session_id": session["session_id"],
                "answer": "In my last project I owned the ingestion pipeline and cut latency by half after profiling.",
                "device_id": "dev-1",
                "request_id": f"turn-{index}",
            },
            headers=headers,
        )
        assert answer.status_code == 200
        payload = answer.json()
        assert "score" not in payload
        if payload["status"] == "completed":
            assert payload["report_id"]
            break
    else:
        pytest.fail("session never completed")

    feedback = await client.post(
        "/agent-interview/feedback",
        json={"session_id": session["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    body = feedback.json()
    assert body["report_status"] == "ready"
    report = body["report"]
    assert report is not None
    assert "overall_score" not in report
    assert all("score" not in competency for competency in report["competencies"])
    assert report["disclosure"]["no_human_review"] is True

    ended = await client.post(
        "/agent-interview/end",
        json={"session_id": session["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert ended.json()["report_id"] == body["report_id"]
