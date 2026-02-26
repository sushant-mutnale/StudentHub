"""
Diagnostic test: prints full response bodies to verify LLM output.
Run with:  pytest backend/tests/test_diagnostic.py -v -s
"""

import pytest
import json
from .conftest import auth_headers


def pretty(label, resp):
    """Print formatted response with status and body."""
    try:
        body = json.dumps(resp.json(), indent=2, default=str)
    except Exception:
        body = resp.text
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Status: {resp.status_code}")
    print(f"{'='*60}")
    print(body[:2000])  # cap to avoid overwhelming output
    print()


# ─────────────── Question Generation (LLM) ───────────────

@pytest.mark.asyncio
async def test_diag_generate_dsa_question(client, student_user, student_token):
    """Does the LLM generate a real DSA question?"""
    resp = await client.post(
        "/questions/generate",
        json={"type": "dsa", "difficulty": "medium", "topic": "arrays"},
        headers=auth_headers(student_token),
    )
    pretty("POST /questions/generate (DSA)", resp)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_diag_evaluate_answer(client, student_user, student_token):
    """Does the LLM evaluate an answer?"""
    resp = await client.post(
        "/questions/evaluate",
        json={
            "question": "What is a binary search tree?",
            "answer": "A BST is a tree data structure where each node has at most two children, and the left subtree contains values less than the parent while the right subtree contains values greater.",
            "type": "dsa",
        },
        headers=auth_headers(student_token),
    )
    pretty("POST /questions/evaluate", resp)
    assert resp.status_code == 200


# ─────────────── Session Orchestrator (LLM) ───────────────

@pytest.mark.asyncio
async def test_diag_session_question_and_answer(client, student_user, student_token):
    """Does the orchestrator generate a real question and evaluate the answer?"""
    # Create
    resp = await client.post(
        "/sessions/create",
        json={"company": "Amazon", "role": "Software Engineer"},
        headers=auth_headers(student_token),
    )
    pretty("POST /sessions/create", resp)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Start
    resp = await client.post(
        f"/sessions/{session_id}/start",
        headers=auth_headers(student_token),
    )
    pretty(f"POST /sessions/{session_id}/start", resp)
    assert resp.status_code == 200

    # Get question
    resp = await client.get(
        f"/sessions/{session_id}/next-question",
        headers=auth_headers(student_token),
    )
    pretty(f"GET /sessions/{session_id}/next-question", resp)
    assert resp.status_code == 200
    q = resp.json()

    if not q.get("interview_completed"):
        # Submit answer
        resp = await client.post(
            f"/sessions/{session_id}/submit-answer",
            json={
                "question_id": q["question_id"],
                "answer": "I would use a hash map for O(1) lookup. First pass: store elements. Second pass: check complements.",
                "time_taken_seconds": 120,
            },
            headers=auth_headers(student_token),
        )
        pretty(f"POST /sessions/{session_id}/submit-answer", resp)
        assert resp.status_code == 200


# ─────────────── Multi-Agent AI (LLM) ───────────────

@pytest.mark.asyncio
async def test_diag_agent_interview(client, student_user, student_token):
    """Does the multi-agent system generate real LLM responses?"""
    # Start
    resp = await client.post(
        "/agent-interview/start",
        json={"company": "Google", "role": "Software Engineer", "difficulty": "medium"},
        headers=auth_headers(student_token),
    )
    pretty("POST /agent-interview/start", resp)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Answer
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I would use dynamic programming to solve this. Break the problem into subproblems and build up the solution bottom-up.",
        },
        headers=auth_headers(student_token),
    )
    pretty("POST /agent-interview/answer", resp)
    assert resp.status_code == 200

    # Hint
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 1},
        headers=auth_headers(student_token),
    )
    pretty("POST /agent-interview/hint", resp)
    assert resp.status_code == 200

    # End
    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id},
        headers=auth_headers(student_token),
    )
    pretty("POST /agent-interview/end", resp)
    assert resp.status_code == 200
