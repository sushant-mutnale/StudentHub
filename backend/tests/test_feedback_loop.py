"""
Tests for F2 — Closed Feedback Loop

Verifies:
1. Click is recorded
2. Save is recorded
3. Dismiss is recorded
4. Apply is recorded (from the apply endpoint)
5. Duplicate events are handled correctly (24h dedup)
6. Feedback belongs to the correct user
7. Feedback affects future ranking (feedback adjustments)
"""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from backend.services.recommendation_engine import (
    recommendation_engine,
    recommendation_feedback_collection,
)
from backend.database import get_database
from backend.config import settings
from jose import jwt


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def _insert_opportunity_job(title="Test Job", skills=None):
    """Insert a job into opportunities_jobs for feedback lookup."""
    db = get_database()
    doc = {
        "_id": ObjectId(),
        "title": title,
        "skills_required": skills or ["python", "react"],
        "company": "TestCo",
        "location": "Remote",
        "apply_by": datetime.utcnow() + timedelta(days=14),
        "is_active": True,
    }
    await db["opportunities_jobs"].insert_one(doc)
    return str(doc["_id"])


async def _clear_feedback(student_id: str):
    """Remove all feedback for a student between tests."""
    await recommendation_feedback_collection().delete_many({
        "student_id": ObjectId(student_id)
    })


# ------------------------------------------------------------------
# 1. Click is recorded
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_click_feedback_recorded(client, student_token):
    payload = _decode_token(student_token)
    student_id = payload["sub"]

    job_id = await _insert_opportunity_job("Click Test Job")
    await _clear_feedback(student_id)

    resp = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "opportunity_id": job_id,
            "opportunity_type": "job",
            "action": "clicked",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"

    fb = await recommendation_feedback_collection().find_one({
        "student_id": ObjectId(student_id),
        "opportunity_id": ObjectId(job_id),
        "action": "clicked",
    })
    assert fb is not None
    await _clear_feedback(student_id)


# ------------------------------------------------------------------
# 2. Save is recorded
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_feedback_recorded(client, student_token):
    payload = _decode_token(student_token)
    student_id = payload["sub"]

    job_id = await _insert_opportunity_job("Save Test Job")
    await _clear_feedback(student_id)

    resp = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "opportunity_id": job_id,
            "opportunity_type": "job",
            "action": "saved",
        },
    )
    assert resp.status_code == 200
    fb = await recommendation_feedback_collection().find_one({
        "student_id": ObjectId(student_id),
        "opportunity_id": ObjectId(job_id),
        "action": "saved",
    })
    assert fb is not None
    await _clear_feedback(student_id)


# ------------------------------------------------------------------
# 3. Dismiss is recorded
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dismiss_feedback_recorded(client, student_token):
    payload = _decode_token(student_token)
    student_id = payload["sub"]

    job_id = await _insert_opportunity_job("Dismiss Test Job")
    await _clear_feedback(student_id)

    resp = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "opportunity_id": job_id,
            "opportunity_type": "job",
            "action": "dismissed",
        },
    )
    assert resp.status_code == 200
    fb = await recommendation_feedback_collection().find_one({
        "student_id": ObjectId(student_id),
        "opportunity_id": ObjectId(job_id),
        "action": "dismissed",
    })
    assert fb is not None
    await _clear_feedback(student_id)


# ------------------------------------------------------------------
# 4. Apply is recorded (via the apply endpoint)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_feedback_recorded_on_job_apply(client, recruiter_token, student_token):

    # Create a job first
    create_resp = await client.post(
        "/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "title": "Apply Feedback Test Job",
            "description": "Testing apply feedback recording",
            "skills_required": ["python"],
            "location": "Remote",
            "visibility": "public",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Clear any prior feedback
    s_payload = _decode_token(student_token)
    await _clear_feedback(s_payload["sub"])

    # Apply
    apply_resp = await client.post(
        f"/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"message": "Testing feedback"},
    )
    assert apply_resp.status_code == 201

    # Verify feedback was recorded
    fb = await recommendation_feedback_collection().find_one({
        "student_id": ObjectId(s_payload["sub"]),
        "opportunity_id": ObjectId(job_id),
        "action": "applied",
    })
    assert fb is not None
    assert fb["opportunity_type"] == "job"
    await _clear_feedback(s_payload["sub"])


# ------------------------------------------------------------------
# 5. Duplicate events are deduplicated (24h window)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_click_feedback_deduplicated(client, student_token):
    payload = _decode_token(student_token)
    student_id = payload["sub"]

    job_id = await _insert_opportunity_job("Dedup Test Job")
    await _clear_feedback(student_id)

    # First click
    resp1 = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "clicked"},
    )
    assert resp1.json()["status"] == "recorded"

    # Duplicate click within 24h — should be skipped
    resp2 = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "clicked"},
    )
    assert resp2.json()["status"] == "skipped"
    assert resp2.json()["reason"] == "duplicate"

    # Only 1 feedback record should exist
    count = await recommendation_feedback_collection().count_documents({
        "student_id": ObjectId(student_id),
        "opportunity_id": ObjectId(job_id),
        "action": "clicked",
    })
    assert count == 1
    await _clear_feedback(student_id)


@pytest.mark.asyncio
async def test_dismiss_not_deduplicated(client, student_token):
    """Dismiss is always recorded (no dedup) since it's an explicit user signal."""
    payload = _decode_token(student_token)
    student_id = payload["sub"]

    job_id = await _insert_opportunity_job("Dismiss No Dedup")
    await _clear_feedback(student_id)

    resp1 = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "dismissed"},
    )
    assert resp1.json()["status"] == "recorded"

    resp2 = await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "dismissed"},
    )
    assert resp2.json()["status"] == "recorded"

    count = await recommendation_feedback_collection().count_documents({
        "student_id": ObjectId(student_id),
        "opportunity_id": ObjectId(job_id),
        "action": "dismissed",
    })
    assert count == 2
    await _clear_feedback(student_id)


# ------------------------------------------------------------------
# 6. Feedback belongs to the correct user (no cross-user contamination)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feedback_isolation_between_users(client, student_token, recruiter_token):
    """Recruiter cannot record feedback on behalf of a student, and vice versa."""

    job_id = await _insert_opportunity_job("Isolation Test Job")

    s_payload = _decode_token(student_token)
    r_payload = _decode_token(recruiter_token)
    await _clear_feedback(s_payload["sub"])

    # Student records feedback
    await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "clicked"},
    )

    # Verify it belongs to student, not recruiter
    fb = await recommendation_feedback_collection().find_one({
        "opportunity_id": ObjectId(job_id),
        "action": "clicked",
    })
    assert fb is not None
    assert str(fb["student_id"]) == s_payload["sub"]
    assert str(fb["student_id"]) != r_payload["sub"]
    await _clear_feedback(s_payload["sub"])


# ------------------------------------------------------------------
# 7. Feedback affects future ranking (feedback adjustments)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feedback_adjustments_boost_positive_skills(client, student_token):
    """
    After saving a Python job, the student should see Python jobs ranked higher
    on the next recommendation call (skill boost of +2 per positive skill).
    """
    from backend.services.recommendation_engine import ScoringEngine

    payload = _decode_token(student_token)
    student_id = payload["sub"]
    await _clear_feedback(student_id)

    # Record a "saved" feedback for a job with "python" skill
    job_id = await _insert_opportunity_job("Python Job", skills=["python", "django"])
    await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "saved"},
    )

    # Verify the feedback is stored
    fb = await recommendation_feedback_collection().find_one({
        "student_id": ObjectId(student_id),
        "action": "saved",
    })
    assert fb is not None
    assert "python" in fb.get("opportunity_skills", [])

    # Now verify the adjustment logic processes the feedback
    # by calling _apply_feedback_adjustments directly with mock scored items
    from backend.services.recommendation_engine import recommendation_engine
    scored_items = [
        {"score": 50, "job": {"skills_required": ["python", "react"]}},
        {"score": 50, "job": {"skills_required": ["java", "spring"]}},
    ]
    adjusted = await recommendation_engine._apply_feedback_adjustments(
        student_id, scored_items, "job"
    )
    # Python job should be boosted (+2 for python), Java job should not
    python_score = next(i["score"] for i in adjusted if "python" in i["job"]["skills_required"])
    java_score = next(i["score"] for i in adjusted if "java" in i["job"]["skills_required"])
    assert python_score > java_score
    await _clear_feedback(student_id)


@pytest.mark.asyncio
async def test_feedback_adjustments_penalize_dismissed_skills(client, student_token):
    """
    After dismissing a job with "react", react-heavy jobs should score lower.
    """
    payload = _decode_token(student_token)
    student_id = payload["sub"]
    await _clear_feedback(student_id)

    job_id = await _insert_opportunity_job("React Job", skills=["react"])
    await client.post(
        "/recommendations/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "dismissed"},
    )

    from backend.services.recommendation_engine import recommendation_engine
    scored_items = [
        {"score": 50, "job": {"skills_required": ["react"]}},
        {"score": 50, "job": {"skills_required": ["python"]}},
    ]
    adjusted = await recommendation_engine._apply_feedback_adjustments(
        student_id, scored_items, "job"
    )
    react_score = next(i["score"] for i in adjusted if "react" in i["job"]["skills_required"])
    python_score = next(i["score"] for i in adjusted if "python" in i["job"]["skills_required"])
    # React should be penalized (-3), python should stay at 50
    assert react_score < python_score
    await _clear_feedback(student_id)
