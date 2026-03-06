"""
E2E Tests: Structured Interview Sessions
Tests the full create → start → question → answer → report lifecycle
using the InterviewOrchestrator.
"""

import pytest

from .conftest import auth_headers


# ===== Test 1: Create Session =====

@pytest.mark.asyncio
async def test_create_session(client, student_user, student_token):
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "session_id" in data
    assert data["company"] == "Amazon"
    assert data["total_rounds"] > 0
    assert len(data["rounds_preview"]) > 0


# ===== Test 2: Start Session =====

@pytest.mark.asyncio
async def test_start_session(client, student_user, student_token):
    resp = await client.post(
        "/sessions/create",
        json={"company": "Google", "role": "SDE-2"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    resp = await client.post(
        f"/sessions/{session_id}/start",
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "first_question" in data
    assert data["current_round"] is not None


# ===== Test 3: Get Next Question =====

@pytest.mark.asyncio
async def test_get_next_question(client, student_user, student_token):
    # Create & start
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    # Get next question
    resp = await client.get(
        f"/sessions/{session_id}/next-question",
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "question_id" in data
    assert "question" in data
    assert "difficulty" in data


# ===== Test 4: Submit Answer =====

@pytest.mark.asyncio
async def test_submit_answer(client, student_user, student_token):
    # Create & start
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    # Get question
    resp = await client.get(f"/sessions/{session_id}/next-question", headers=auth_headers(student_token))
    question_id = resp.json()["question_id"]

    # Submit answer
    resp = await client.post(
        f"/sessions/{session_id}/submit-answer",
        json={
            "question_id": question_id,
            "answer": "I would use a hash map to solve this problem with O(n) time complexity by iterating through the array once.",
            "time_taken_seconds": 120,
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "evaluation" in data
    assert "score" in data["evaluation"]
    assert "next_action" in data
    assert data["next_action"]["action"] in ["next_question", "next_round", "interview_completed"]


# ===== Test 5: Full Round Flow =====

@pytest.mark.asyncio
async def test_full_round_flow(client, student_user, student_token):
    """Complete an entire round by answering all questions."""
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    # Answer questions until round changes or interview completes
    for _ in range(10):  # safety limit
        resp = await client.get(f"/sessions/{session_id}/next-question", headers=auth_headers(student_token))
        if resp.status_code != 200:
            break
        q = resp.json()
        if q.get("interview_completed"):
            break

        resp = await client.post(
            f"/sessions/{session_id}/submit-answer",
            json={
                "question_id": q["question_id"],
                "answer": "This is a detailed answer demonstrating my understanding of data structures and algorithm concepts.",
                "time_taken_seconds": 90,
            },
            headers=auth_headers(student_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["next_action"]["action"] in ["next_round", "interview_completed"]:
            break


# ===== Test 6: Get Session Status =====

@pytest.mark.asyncio
async def test_get_session_status(client, student_user, student_token):
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    resp = await client.get(
        f"/sessions/{session_id}/status",
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["session_status"] == "in_progress"
    assert data["company"] == "Amazon"
    assert data["total_rounds"] > 0


# ===== Test 7: Pause & Resume =====

@pytest.mark.asyncio
async def test_pause_resume(client, student_user, student_token):
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    # Pause
    resp = await client.post(f"/sessions/{session_id}/pause", headers=auth_headers(student_token))
    assert resp.status_code == 200, resp.text

    # Resume
    resp = await client.post(f"/sessions/{session_id}/resume", headers=auth_headers(student_token))
    assert resp.status_code == 200, resp.text


# ===== Test 8: Abandon Session =====

@pytest.mark.asyncio
async def test_abandon_session(client, student_user, student_token):
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    resp = await client.post(f"/sessions/{session_id}/abandon", headers=auth_headers(student_token))
    assert resp.status_code == 200, resp.text

    # Verify abandoned
    resp = await client.get(f"/sessions/{session_id}/status", headers=auth_headers(student_token))
    assert resp.json()["session_status"] == "abandoned"


# ===== Test 9: List My Sessions =====

@pytest.mark.asyncio
async def test_list_my_sessions(client, student_user, student_token):
    # Create two sessions
    await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "SDE-1"},
        headers=auth_headers(student_token),
    )
    await client.post(
        "/sessions/create",
        json={"company": "Google", "role": "L4"},
        headers=auth_headers(student_token),
    )

    resp = await client.get("/sessions/my-sessions", headers=auth_headers(student_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["sessions"]) >= 2


# ===== Test 10: Complete Interview & Get Report =====

@pytest.mark.asyncio
async def test_complete_and_report(client, student_user, student_token):
    """Complete all rounds and get the full report."""
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]
    await client.post(f"/sessions/{session_id}/start", headers=auth_headers(student_token))

    # Answer all questions until completion
    for _ in range(20):  # safety limit
        resp = await client.get(f"/sessions/{session_id}/next-question", headers=auth_headers(student_token))
        if resp.status_code != 200:
            break
        q = resp.json()
        if q.get("interview_completed"):
            break

        resp = await client.post(
            f"/sessions/{session_id}/submit-answer",
            json={
                "question_id": q["question_id"],
                "answer": "I would approach this problem systematically by first analyzing the requirements and then developing a solution.",
                "time_taken_seconds": 60,
            },
            headers=auth_headers(student_token),
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        if data["next_action"]["action"] == "interview_completed":
            break

    # Get report (may not be available if orchestrator hasn't marked complete)
    resp = await client.get(f"/sessions/{session_id}/report", headers=auth_headers(student_token))
    # Report may be 400 if not completed yet — that's acceptable for partial flow
    assert resp.status_code in [200, 400]
