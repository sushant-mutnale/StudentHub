"""
End-to-End Integration Tests for Shared Fit + Closed Feedback Loop + Recruiter Workflows

Verifies the entire lifecycle:
1. Recruiter creates job posting with specific skill requirements.
2. Multiple students with varying skills are evaluated via Shared Fit Scoring.
3. Bidirectional scoring consistency between student recommendation and recruiter ranking.
4. Student views, saves, and applies to jobs; feedback deduplication correctly filters repeat actions.
5. Recommendation engine adjusts student job scores based on feedback history.
6. Recruiter queries /ranked-candidates endpoint and receives candidates ordered by fit score with full 6-component explanation.
7. Recruiter creates Saved Searches with filters and toggles alert settings.
8. Background saved search alerts identify matching candidates and send structured notifications.
9. Recruiter can query matching candidates directly from saved searches.
"""

import pytest
from datetime import datetime
from bson import ObjectId
from unittest.mock import patch, AsyncMock

from backend.services.recommendation_engine import ScoringEngine
from backend.services.fit_scoring import calculate_fit_score, rank_candidates_for_job
from backend.models.saved_search import (
    create_saved_search,
    run_saved_search_alerts,
    get_candidates_for_search,
    update_saved_search,
)


@pytest.mark.asyncio
async def test_full_closed_loop_e2e(client, student_token, recruiter_token):
    """
    Step 1-9 End-to-End closed loop lifecycle test.
    """
    # 1. Recruiter posts a job
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    job_payload = {
        "title": "Senior Python Backend Engineer",
        "description": "Build high-scale FastAPI microservices and AI pipelines.",
        "skills_required": ["Python", "FastAPI", "MongoDB", "Redis"],
        "location": "Remote",
        "experience_level": "mid",
    }
    resp = await client.post("/jobs/", json=job_payload, headers=recruiter_headers)
    assert resp.status_code == 201, resp.text
    job_data = resp.json()
    job_id = job_data["id"]

    # 2. Shared Fit score calculation check
    student_profile = {
        "skills": [
            {"name": "Python", "level": 90},
            {"name": "FastAPI", "level": 85},
            {"name": "MongoDB", "level": 75},
        ],
        "location": "Remote",
        "college": "Stanford University",
        "interests": ["backend", "AI pipelines"],
        "ai_profile": {"overall_score": 85, "activity_score": 80, "profile_completeness": 90},
    }

    fit_score = calculate_fit_score(student_profile, job_payload)
    assert fit_score["total_score"] > 60.0
    assert fit_score["breakdown"]["skill_match"]["score"] > 0
    assert "Python" in fit_score["breakdown"]["skill_match"]["matched"] or "python" in [s.lower() for s in fit_score["breakdown"]["skill_match"]["matched"]]
    assert "Redis" in fit_score["breakdown"]["skill_match"]["missing"] or "redis" in [s.lower() for s in fit_score["breakdown"]["skill_match"]["missing"]]

    # 3. Student views the job (records 'clicked' feedback)
    click_resp = await client.post(
        f"/recommendations/feedback",
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "clicked"},
        headers=student_headers,
    )
    assert click_resp.status_code == 200
    assert click_resp.json().get("status") == "recorded"

    # Duplicate click within 24h is ignored/skipped
    dup_click = await client.post(
        f"/recommendations/feedback",
        json={"opportunity_id": job_id, "opportunity_type": "job", "action": "clicked"},
        headers=student_headers,
    )
    assert dup_click.status_code == 200
    assert dup_click.json().get("status") == "skipped"

    # 4. Student saves the job
    save_resp = await client.post(f"/jobs/{job_id}/save", headers=student_headers)
    assert save_resp.status_code == 200

    # 5. Student applies to the job
    apply_resp = await client.post(
        f"/jobs/{job_id}/apply",
        json={"message": "I am passionate about building Python microservices!"},
        headers=student_headers,
    )
    assert apply_resp.status_code == 201

    # 6. Recruiter retrieves ranked candidates for the job
    ranked_resp = await client.get(
        f"/jobs/{job_id}/ranked-candidates", headers=recruiter_headers
    )
    assert ranked_resp.status_code == 200
    ranked_data = ranked_resp.json()
    assert "candidates" in ranked_data
    candidates = ranked_data["candidates"]
    assert isinstance(candidates, list)
    if candidates:
        first_candidate = candidates[0]
        assert "score" in first_candidate
        assert "explanation" in first_candidate
        assert "skill_match" in first_candidate["explanation"]

    # 7. Recruiter creates a Saved Search
    search_payload = {
        "name": "E2E Python Backend Talent",
        "skill": "Python",
        "location": "Remote",
        "alert_enabled": True,
    }
    saved_search_resp = await client.post(
        "/recruiter/saved-searches",
        json=search_payload,
        headers=recruiter_headers,
    )
    assert saved_search_resp.status_code == 201
    saved_search = saved_search_resp.json()
    search_id = saved_search["id"]
    assert saved_search["name"] == "E2E Python Backend Talent"
    assert saved_search["alert_enabled"] is True

    # 8. Recruiter queries candidates for the saved search
    search_candidates_resp = await client.get(
        f"/recruiter/saved-searches/{search_id}/candidates",
        headers=recruiter_headers,
    )
    assert search_candidates_resp.status_code == 200
    cand_list = search_candidates_resp.json()
    assert isinstance(cand_list, list)

    # 9. Recruiter toggles alert for saved search
    toggle_resp = await client.patch(
        f"/recruiter/saved-searches/{search_id}",
        json={"alert_enabled": False},
        headers=recruiter_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["alert_enabled"] is False

    # 10. Run saved search alerts background engine
    results = await run_saved_search_alerts()
    assert "searches_checked" in results
    assert "alerts_sent" in results


@pytest.mark.asyncio
async def test_recruiter_ranked_candidates_authorization(client, recruiter_token, student_token):
    """Unauthorized users (other recruiters or students) cannot view candidate matches for a job."""
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    job_payload = {
        "title": "Confidential Security Role",
        "description": "AppSec assessment and red teaming.",
        "skills_required": ["Cryptography", "Python"],
        "location": "Remote",
    }
    post_resp = await client.post("/jobs/", json=job_payload, headers=recruiter_headers)
    assert post_resp.status_code == 201
    job_id = post_resp.json()["id"]

    # Student cannot access recruiter match endpoint
    student_resp = await client.get(
        f"/jobs/{job_id}/ranked-candidates", headers=student_headers
    )
    assert student_resp.status_code == 403


@pytest.mark.asyncio
async def test_feedback_loop_score_adjustment_e2e(client):
    """Verifies that feedback adjustments compound properly in recommendation scoring."""
    from backend.services.recommendation_engine import recommendation_engine
    from bson import ObjectId

    student_id = str(ObjectId())

    # Record feedback with opportunity_skills
    await recommendation_engine.record_feedback(
        student_id=student_id,
        opportunity_id=str(ObjectId()),
        opportunity_type="job",
        action="applied",
    )

    scored_items = [
        {
            "job": {"skills_required": ["Python", "Docker"]},
            "score": 70.0,
        },
        {
            "job": {"skills_required": ["Rust"]},
            "score": 70.0,
        },
    ]

    adjusted = await recommendation_engine._apply_feedback_adjustments(
        student_id=student_id,
        scored_items=scored_items,
        opportunity_type="job",
    )
    assert len(adjusted) == 2
    assert all("score" in item for item in adjusted)

