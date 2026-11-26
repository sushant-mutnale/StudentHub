"""
E2E Tests: Multi-Agent AI Interview System
Tests the agent-based interview simulation with start → answer → hints → end flow.
"""

import pytest

from .conftest import auth_headers


# ===== Test 1: Start Agent Interview =====

@pytest.mark.asyncio
async def test_start_agent_interview(client, student_user, student_token):
    resp = await client.post(
        "/agent-interview/start",
        json={
            "company": "Google",
            "role": "Software Engineer",
            "difficulty": "medium",
            "device_id": "test-device",
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "session_id" in data
    assert "interviewer_message" in data


# ===== Test 2: Submit Answer =====

@pytest.mark.asyncio
async def test_submit_answer_agent(client, student_user, student_token):
    # Start
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Amazon", "role": "SDE-2", "difficulty": "easy", "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    # Answer
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I would use a hash map to track the frequency of each element, then iterate to find the most frequent one.",
            "device_id": "test-device",
            "request_id": "answer-1",
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "next_question" in data
    assert "score" not in data


# ===== Test 3: Request Hint =====

@pytest.mark.asyncio
async def test_request_hint(client, student_user, student_token):
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Google", "role": "Software Engineer", "difficulty": "medium", "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    # Request hint level 1
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 1, "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "hint" in data
    assert data["hints_used"] == 1

    # Request hint level 2
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 2, "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["hints_used"] == 1


# ===== Test 4: End Interview =====

@pytest.mark.asyncio
async def test_end_interview(client, student_user, student_token):
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Amazon", "role": "Software Engineer", "difficulty": "easy", "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id, "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["report_id"] and data["report_status"] in ("evaluating", "ready", "suppressed")


# ===== Test 5: Full Agent Flow =====

@pytest.mark.asyncio
async def test_full_agent_flow(client, student_user, student_token):
    """Start → Answer 3 questions → End."""
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Microsoft", "role": "SDE-1", "difficulty": "easy", "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Answer 3 questions
    for i in range(3):
        resp = await client.post(
            "/agent-interview/answer",
            json={
                "session_id": session_id,
                "answer": f"For question {i+1}, I would use an iterative approach with clear separation of concerns to handle the problem efficiently.",
                "device_id": "test-device",
                "request_id": f"flow-{i+1}",
            },
            headers=auth_headers(student_token),
        )
        assert resp.status_code == 200, f"Answer {i+1} failed: {resp.text}"

    # End
    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id, "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200

    wrong_device = await client.post(
        "/agent-interview/feedback",
        json={"session_id": session_id, "device_id": "wrong-device"},
        headers=auth_headers(student_token),
    )
    assert wrong_device.status_code == 409, wrong_device.text
    assert wrong_device.json()["detail"]["code"] == "device_conflict"

    correct_device = await client.post(
        "/agent-interview/feedback",
        json={"session_id": session_id, "device_id": "test-device"},
        headers=auth_headers(student_token),
    )
    assert correct_device.status_code == 200, correct_device.text


# ===== Test 6: Demo Endpoints (No Auth) =====

@pytest.mark.asyncio
async def test_demo_endpoints(client):
    """Test demo endpoints that don't require authentication."""
    # Demo start (POST with query params)
    resp = await client.post(
        "/agent-interview/demo/start",
        params={"company": "Google", "role": "Software Engineer", "difficulty": "easy"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    session_id = data["session_id"]

    # Demo answer (POST with query params)
    resp = await client.post(
        "/agent-interview/demo/answer",
        params={"session_id": session_id, "answer": "I would implement this using a binary search tree for efficient lookup operations."},
    )
    assert resp.status_code == 200, resp.text

    # Demo end (POST with query params)
    resp = await client.post(
        "/agent-interview/demo/end",
        params={"session_id": session_id},
    )
    assert resp.status_code == 200, resp.text


# ===== Test 7: Get Agent Info =====

@pytest.mark.asyncio
async def test_get_agent_info(client):
    resp = await client.get("/agent-interview/agents")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "agents" in data
    # Should have multiple agents
    assert len(data["agents"]) >= 3


# ===== Test 8: DSA Stage-by-Stage Interview Flow =====

@pytest.mark.asyncio
async def test_dsa_stage_by_stage_flow(student_user):
    from backend.services.multi_agent_system import multi_agent_interview

    session_id = f"dsa-{student_user['_id']}"
    await multi_agent_interview.start(
        session_id=session_id, student_id=str(student_user["_id"]),
        company="Google", role="Software Engineer", difficulty="medium",
        interview_type="dsa", resume_text="",
    )
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "clarification"

    await multi_agent_interview.answer(session_id, "What are the input size limits?")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "approach"

    await multi_agent_interview.answer(session_id, "I will use two pointers with O(N) time.")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "coding"

    await multi_agent_interview.answer(session_id, "def solve(arr):\n    return arr")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "optimization"

    await multi_agent_interview.answer(session_id, "I would return early for an empty array.")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "completed"


@pytest.mark.asyncio
async def test_clarification_request_returns_blueprint_reply(client, student_user, student_token):
    from backend.interview_engine.domain.behavioral_blueprint import build_behavioral_blueprint

    resp = await client.post(
        "/agent-interview/start",
        json={
            "company": "Google",
            "role": "Software Engineer",
            "difficulty": "medium",
            "device_id": "test-device",
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    session_id = resp.json()["session_id"]
    expected_reply = build_behavioral_blueprint("practice", "Software Engineer").ordered_slots()[0].clarification_text

    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "Could you clarify the question?",
            "device_id": "test-device",
            "request_id": "clarification-1",
            "kind": "clarification_request",
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    reply = resp.json()["reply"]
    assert isinstance(reply, str) and reply
    assert reply == expected_reply


# ===== Test 9: Voice Interview Helper Logic =====

@pytest.mark.asyncio
async def test_voice_helper_logic(student_user):
    from backend.routes.agent_routes import (
        start_agent_interview_logic,
        submit_answer_logic,
        end_agent_interview_logic
    )
    
    student_id = str(student_user["_id"])
    
    # Start voice agent interview
    session = await start_agent_interview_logic(
        student_id=student_id,
        company="Microsoft",
        role="Developer",
        difficulty="easy",
        interview_type="dsa"
    )
    assert "session_id" in session
    assert "interviewer_message" in session
    session_id = session["session_id"]
    
    # Submit answer
    answer_res = await submit_answer_logic(
        session_id=session_id,
        answer="Does the array contain duplicates?"
    )
    assert answer_res["status"] == "active"
    assert "evaluation" in answer_res
    assert answer_res["dsa_stage"] == "approach"
    
    # End interview
    final_res = await end_agent_interview_logic(session_id)
    assert "final_score" in final_res
    assert "career_coaching" in final_res
