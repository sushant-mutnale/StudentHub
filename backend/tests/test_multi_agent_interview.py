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
        json={"company": "Amazon", "role": "SDE-2", "difficulty": "easy"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    # Answer
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I would use a hash map to track the frequency of each element, then iterate to find the most frequent one.",
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "evaluation" in data
    assert "next_question" in data or "message" in data


# ===== Test 3: Request Hint =====

@pytest.mark.asyncio
async def test_request_hint(client, student_user, student_token):
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Google", "role": "Software Engineer", "difficulty": "medium"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    # Request hint level 1
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 1},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "hint" in data

    # Request hint level 2
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 2},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text


# ===== Test 4: End Interview =====

@pytest.mark.asyncio
async def test_end_interview(client, student_user, student_token):
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Amazon", "role": "Software Engineer", "difficulty": "easy"},
        headers=auth_headers(student_token),
    )
    session_id = resp.json()["session_id"]

    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "final_score" in data or "overall_score" in data or "performance" in data


# ===== Test 5: Full Agent Flow =====

@pytest.mark.asyncio
async def test_full_agent_flow(client, student_user, student_token):
    """Start → Answer 3 questions → End."""
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Microsoft", "role": "SDE-1", "difficulty": "easy"},
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
            },
            headers=auth_headers(student_token),
        )
        assert resp.status_code == 200, f"Answer {i+1} failed: {resp.text}"

    # End
    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200


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
async def test_dsa_stage_by_stage_flow(client, student_user, student_token):
    # Start DSA interview
    resp = await client.post(
        "/agent-interview/start",
        json={
            "company": "Google",
            "role": "Software Engineer",
            "difficulty": "medium",
            "interview_type": "dsa"
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    session_id = data["session_id"]
    assert "session_id" in data
    
    # Verify stage starts at clarification by checking context
    from backend.services.multi_agent_system import multi_agent_interview
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "clarification"
    
    # 1. Answer clarification stage -> approach
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "What are the input size limits? Can the array contain negative numbers?"
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    res = resp.json()
    assert "evaluation" in res
    
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "approach"
    
    # 2. Answer approach stage -> coding
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I will use a two-pointer approach with O(N) time complexity and O(1) space complexity."
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "coding"
    
    # 3. Answer coding stage -> optimization
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "def solve(arr):\n    left, right = 0, len(arr)-1\n    return arr"
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "optimization"
    
    # 4. Answer optimization stage -> completed
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I would handle empty array by returning early, and null checks for safety."
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    res = resp.json()
    assert res["next_question"] == ""
    
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "completed"


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
