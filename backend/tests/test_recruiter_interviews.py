"""
E2E Tests: Recruiter Interview Lifecycle
Tests the full propose → accept/decline → reschedule → cancel → feedback flow.
"""

import pytest
from datetime import datetime, timedelta

from .conftest import auth_headers, make_token


# ---------- Helper ----------

def make_proposed_times():
    """Generate two proposed time slots in the future."""
    now = datetime.utcnow()
    return [
        {
            "start": (now + timedelta(days=3)).isoformat(),
            "end": (now + timedelta(days=3, hours=1)).isoformat(),
            "timezone": "UTC",
        },
        {
            "start": (now + timedelta(days=5)).isoformat(),
            "end": (now + timedelta(days=5, hours=1)).isoformat(),
            "timezone": "UTC",
        },
    ]


def interview_payload(candidate_id: str, job_id: str = None):
    payload = {
        "candidate_id": candidate_id,
        "proposed_times": make_proposed_times(),
        "location": {"type": "online", "url": "https://meet.example.com/room1"},
        "description": "First round technical interview",
    }
    if job_id:
        payload["job_id"] = job_id
    return payload


# ===== Test 1: Create Interview =====

@pytest.mark.asyncio
async def test_create_interview(client, recruiter_user, student_user, recruiter_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post(
        "/interviews",
        json=payload,
        headers=auth_headers(recruiter_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "proposed"
    assert data["candidate_id"] == str(student_user["_id"])
    assert data["recruiter_id"] == str(recruiter_user["_id"])
    assert len(data["proposed_times"]) == 2
    assert data["description"] == "First round technical interview"


# ===== Test 2: List My Interviews =====

@pytest.mark.asyncio
async def test_list_my_interviews(client, recruiter_user, student_user, recruiter_token, student_token):
    # Create one interview first
    payload = interview_payload(str(student_user["_id"]))
    await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))

    # Recruiter sees it
    resp = await client.get("/interviews/my", headers=auth_headers(recruiter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["interviews"]) == 1

    # Student sees it
    resp = await client.get("/interviews/my", headers=auth_headers(student_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["interviews"]) == 1
    assert data["interviews"][0]["status"] == "proposed"


# ===== Test 3: Accept Interview =====

@pytest.mark.asyncio
async def test_accept_interview(client, recruiter_user, student_user, recruiter_token, student_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    # Accept with slot_index=0
    resp = await client.post(
        f"/interviews/{interview_id}/accept",
        json={"slot_index": 0},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["scheduled_slot"] is not None


# ===== Test 4: Decline Interview =====

@pytest.mark.asyncio
async def test_decline_interview(client, recruiter_user, student_user, recruiter_token, student_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    resp = await client.post(
        f"/interviews/{interview_id}/decline",
        json={"reason": "Schedule conflict"},
        headers=auth_headers(student_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "declined"


# ===== Test 5: Reschedule Interview =====

@pytest.mark.asyncio
async def test_reschedule_interview(client, recruiter_user, student_user, recruiter_token, student_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    # Accept first
    await client.post(
        f"/interviews/{interview_id}/accept",
        json={"slot_index": 0},
        headers=auth_headers(student_token),
    )

    # Recruiter reschedules
    new_times = make_proposed_times()
    resp = await client.post(
        f"/interviews/{interview_id}/reschedule",
        json={"proposed_times": new_times, "note": "Need to push back"},
        headers=auth_headers(recruiter_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rescheduled"
    assert data["scheduled_slot"] is None  # cleared on reschedule


# ===== Test 6: Cancel Interview =====

@pytest.mark.asyncio
async def test_cancel_interview(client, recruiter_user, student_user, recruiter_token, student_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    resp = await client.post(
        f"/interviews/{interview_id}/cancel",
        json={"reason": "Position filled"},
        headers=auth_headers(recruiter_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# ===== Test 7: Submit Feedback =====

@pytest.mark.asyncio
async def test_submit_feedback(client, recruiter_user, student_user, recruiter_token, student_token):
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    resp = await client.post(
        f"/interviews/{interview_id}/feedback",
        json={"rating": 4, "comment": "Strong technical skills"},
        headers=auth_headers(recruiter_token),
    )
    assert resp.status_code == 200


# ===== Test 8: Unauthorized Access =====

@pytest.mark.asyncio
async def test_unauthorized_access(client, recruiter_user, student_user, recruiter_token, student_token):
    # Create interview
    payload = interview_payload(str(student_user["_id"]))
    resp = await client.post("/interviews", json=payload, headers=auth_headers(recruiter_token))
    interview_id = resp.json()["id"]

    # Create a third user who is not a participant
    from backend.database import get_database
    from backend.utils.auth import hash_password
    from bson import ObjectId
    db = get_database()
    outsider = {
        "_id": ObjectId(),
        "role": "student",
        "username": "outsider",
        "email": "outsider@test.com",
        "password_hash": hash_password("Test@123"),
        "full_name": "Outsider Student",
        "skills": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db["users"].insert_one(outsider)
    outsider_token = make_token(outsider)

    # Outsider tries to view interview → 403
    resp = await client.get(
        f"/interviews/{interview_id}",
        headers=auth_headers(outsider_token),
    )
    assert resp.status_code == 403
