"""
E2E Tests: Question Generation & Answer Evaluation
Tests standalone question generation and evaluation endpoints.
"""

import pytest

from .conftest import auth_headers


# ===== Test 1: Generate DSA Question =====

@pytest.mark.asyncio
async def test_generate_dsa_question(client, student_user, student_token):
    resp = await client.get(
        "/questions/dsa",
        params={"difficulty": "medium", "topic": "arrays"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "question" in data
    q = data["question"]
    assert "title" in q or "question" in q or "description" in q


# ===== Test 2: Generate Behavioral Question =====

@pytest.mark.asyncio
async def test_generate_behavioral_question(client, student_user, student_token):
    resp = await client.get(
        "/questions/behavioral",
        params={"theme": "leadership"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "question" in data


# ===== Test 3: Generate Design Question =====

@pytest.mark.asyncio
async def test_generate_design_question(client, student_user, student_token):
    resp = await client.get(
        "/questions/design",
        params={"difficulty": "medium"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "question" in data


# ===== Test 4: Evaluate Answer =====

@pytest.mark.asyncio
async def test_evaluate_answer(client, student_user, student_token):
    # First generate a question
    resp = await client.get(
        "/questions/dsa",
        params={"difficulty": "easy"},
        headers=auth_headers(student_token),
    )
    question = resp.json()["question"]

    # Now evaluate an answer
    resp = await client.post(
        "/questions/evaluate",
        json={
            "question": question,
            "answer": "I would solve this using a two-pointer approach. Start one pointer at the beginning and one at the end. Compare elements and move inward. This gives O(n) time and O(1) space.",
            "time_taken_seconds": 180,
        },
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "score" in data
    assert "grade" in data
    assert isinstance(data["score"], (int, float))
    assert data["grade"] in ["A", "B", "C", "D", "F"]
    assert "feedback" in data
    assert "strengths" in data
    assert "improvements" in data


# ===== Test 5: Quick Endpoints (No Auth) =====

@pytest.mark.asyncio
async def test_quick_endpoints(client):
    """Test quick question endpoints that don't require authentication."""
    # Quick DSA
    resp = await client.get("/questions/quick/dsa")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "question" in data

    # Quick Behavioral
    resp = await client.get("/questions/quick/behavioral")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "question" in data

    # Quick Design
    resp = await client.get("/questions/quick/design")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "title" in data
