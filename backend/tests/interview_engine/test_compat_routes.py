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
from backend.interview_engine.contracts.messages import SessionView, SubmitTurnResult
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
async def test_start_requires_device_id(client, student_token):
    response = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "device_id_required"


@pytest.mark.asyncio
async def test_full_legacy_flow(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Senior Engineer", "company": "Acme", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    assert start.status_code == 200
    body = start.json()
    assert body["session_id"]
    assert body["question"] == body["interviewer_message"]
    assert "score" not in body

    answer = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": body["session_id"],
            "answer": "I led the migration and cut errors by half.",
            "device_id": "dev-1",
            "request_id": "turn-1",
        },
        headers=headers,
    )
    assert answer.status_code == 200
    answered = answer.json()
    assert answered["next_question"]
    assert "evaluation" not in answered or "score" not in answered.get("evaluation", {})

    hint = await client.post(
        "/agent-interview/hint",
        json={"session_id": body["session_id"], "level": 1, "device_id": "dev-1"},
        headers=headers,
    )
    assert hint.status_code == 200
    assert hint.json()["hint"]
    assert "score_penalty" not in hint.json()

    end = await client.post(
        "/agent-interview/end",
        json={"session_id": body["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert end.status_code == 200
    ended = end.json()
    assert ended["report_id"]
    assert ended["report_status"] == "evaluating"
    assert "final_score" not in ended

    feedback = await client.post(
        "/agent-interview/feedback",
        json={"session_id": body["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert feedback.status_code == 200
    assert feedback.json()["report_status"] in ("evaluating", "ready")
    assert "overall_score" not in feedback.json()


@pytest.mark.asyncio
async def test_answer_requires_matching_device(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    body = start.json()
    conflict = await client.post(
        "/agent-interview/answer",
        json={"session_id": body["session_id"], "answer": "text", "device_id": "dev-2", "request_id": "t1"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "device_conflict"


@pytest.mark.asyncio
async def test_resume_returns_new_token_and_question(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    body = start.json()
    resumed = await client.post(
        "/agent-interview/resume",
        json={"session_id": body["session_id"], "device_id": "dev-2"},
        headers=headers,
    )
    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["fencing_token"] != body["fencing_token"]
    assert payload["question"] == body["question"]


class _PendingEngine:
    async def submit_turn(self, cmd):
        return SubmitTurnResult(
            session_id="s1", status="in_progress", next_action="next_slot",
            question_pending=True,
        )

    async def load_owned(self, session_id, candidate_id):
        return object()

    async def session_view(self, record):
        return SessionView(
            session_id="s1", status="in_progress", version=1,
            question_pending=True,
        )


@pytest.mark.asyncio
async def test_answer_returns_202_when_question_is_pending(client, student_token):
    previous = app.dependency_overrides.get(get_engine)
    app.dependency_overrides[get_engine] = lambda: _PendingEngine()
    try:
        response = await client.post(
            "/agent-interview/answer",
            json={
                "session_id": "s1", "answer": "text", "device_id": "dev-1",
                "request_id": "t1",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_engine, None)
        else:
            app.dependency_overrides[get_engine] = previous
    assert response.status_code == 202
    assert response.json()["question_pending"] is True
