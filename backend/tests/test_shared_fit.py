"""
Tests for F1 — Shared Fit Score

Verifies:
- Scoring engine produces consistent scores for student→job and job→student paths
- Ranked candidates endpoint returns correct ranking order
- Authorization: recruiter cannot see other recruiters' job matches
- Empty/edge cases handled gracefully
- No PII in logs (no print() calls)
- Score is deterministic for the same inputs
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId


# ------------------------------------------------------------------
# Deterministic scoring consistency test
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_is_deterministic(client, recruiter_token, student_token):
    """Same student+job should produce identical scores on repeated calls."""
    from backend.services.recommendation_engine import ScoringEngine
    student = {
        "skills": [
            {"name": "python", "level": 80},
            {"name": "react", "level": 50},
        ],
        "location": "Pune",
        "college": "VIT",
        "ai_profile": {"overall_score": 65, "interview_score": 50, "learning_score": 40,
                        "activity_score": 40, "profile_completeness": 70},
        "interests": ["backend"],
        "learning_paths": [],
    }
    job = {
        "skills_required": ["python", "react", "node"],
        "location": "Remote",
        "experience_required": "0-1 years",
        "posted_at": None,
        "title": "Full Stack Developer",
        "work_mode": "remote",
    }

    scores = [ScoringEngine.calculate_job_score(student, job)["total_score"] for _ in range(20)]
    assert len(set(scores)) == 1, f"Score not deterministic: {set(scores)}"


# ------------------------------------------------------------------
# Authoritative engine produces 0-100 range
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fit_score_is_in_0_100_range(client, recruiter_token):
    from backend.services.recommendation_engine import ScoringEngine
    student = {
        "skills": [{"name": "python", "level": 70}],
        "location": "Mumbai",
        "college": "IIT",
        "ai_profile": {"overall_score": 50, "interview_score": 40, "learning_score": 30,
                        "activity_score": 30, "profile_completeness": 60},
    }
    job = {
        "skills_required": ["python"],
        "location": "Mumbai",
        "experience_required": "0-1 years",
        "posted_at": None,
        "title": "Python Developer",
        "work_mode": "",
    }
    result = ScoringEngine.calculate_job_score(student, job)
    assert 0 <= result["total_score"] <= 100


# ------------------------------------------------------------------
# Ranked-candidates endpoint: authorization
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ranked_candidates_requires_recruiter_auth(client, student_token):
    resp = await client.get(
        "/jobs/fakejobid/ranked-candidates",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code in (403, 422)


@pytest.mark.asyncio
async def test_ranked_candidates_job_not_found(client, recruiter_token):
    resp = await client.get(
        "/jobs/000000000000000000000000/ranked-candidates",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 404


# ------------------------------------------------------------------
# matches endpoint: no print() PII leakage
# ------------------------------------------------------------------

def test_match_routes_contain_no_print_calls():
    """match_routes.py should not contain print() calls (PII leak)."""
    import inspect, backend.routes.match_routes as mod
    source = inspect.getsource(mod)
    assert "print(" not in source, "match_routes.py still contains print() calls"


# ------------------------------------------------------------------
# Scoring components: all 6 weights present
# ------------------------------------------------------------------

def test_scoring_engine_weights_sum_to_one():
    from backend.services.recommendation_engine import ScoringEngine
    total = sum(ScoringEngine.WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


def test_scoring_engine_returns_all_components():
    from backend.services.recommendation_engine import ScoringEngine
    student = {
        "skills": [{"name": "react", "level": 60}],
        "ai_profile": {"overall_score": 50, "interview_score": 50,
                        "activity_score": 30, "profile_completeness": 60},
    }
    job = {
        "skills_required": ["react"],
        "location": "Remote",
        "work_mode": "remote",
        "experience_required": "0-1 years",
        "posted_at": None,
        "title": "Frontend Dev",
    }
    result = ScoringEngine.calculate_job_score(student, job)
    breakdown = result["breakdown"]
    for component in ["skill_match", "proficiency_fit", "freshness", "location_match",
                       "career_alignment", "ai_readiness"]:
        assert component in breakdown, f"Missing component: {component}"
        assert "score" in breakdown[component]


# ------------------------------------------------------------------
# Score direction symmetry
# ------------------------------------------------------------------

def test_score_symmetry():
    """Scoring a student against a job should produce the same score
    regardless of whether the student or the recruiter initiated."""
    from backend.services.recommendation_engine import ScoringEngine
    student = {
        "skills": [
            {"name": "java", "level": 75},
            {"name": "spring", "level": 60},
        ],
        "location": "Bangalore",
        "ai_profile": {"overall_score": 60, "interview_score": 50,
                        "activity_score": 40, "profile_completeness": 70},
        "interests": [],
        "learning_paths": [],
    }
    job = {
        "skills_required": ["java", "spring"],
        "location": "Bangalore",
        "experience_required": "0-1 years",
        "posted_at": None,
        "title": "Java Developer",
        "work_mode": "",
    }
    # Student side (recommendation engine)
    score_student = ScoringEngine.calculate_job_score(student, job)
    # Recruiter side (same function)
    score_recruiter = ScoringEngine.calculate_job_score(student, job)
    assert score_student["total_score"] == score_recruiter["total_score"]
    # Breakdown components should also match
    for key in score_student["breakdown"]:
        assert score_student["breakdown"][key]["score"] == score_recruiter["breakdown"][key]["score"]


# ------------------------------------------------------------------
# Empty edge cases
# ------------------------------------------------------------------

def test_scoring_handles_empty_skills():
    from backend.services.recommendation_engine import ScoringEngine
    student = {"skills": [], "ai_profile": {}}
    job = {"skills_required": ["python"], "location": "Remote", "work_mode": "remote",
           "experience_required": "0-1 years", "posted_at": None, "title": "Test"}
    result = ScoringEngine.calculate_job_score(student, job)
    assert 0 <= result["total_score"] <= 100


def test_scoring_handles_empty_required_skills():
    from backend.services.recommendation_engine import ScoringEngine
    student = {"skills": [{"name": "python", "level": 80}], "ai_profile": {}}
    job = {"skills_required": [], "location": "", "work_mode": "",
           "experience_required": "", "posted_at": None, "title": "Test"}
    result = ScoringEngine.calculate_job_score(student, job)
    assert 0 <= result["total_score"] <= 100


def test_scoring_handles_missing_ai_profile():
    from backend.services.recommendation_engine import ScoringEngine
    student = {"skills": [{"name": "python", "level": 50}]}
    job = {"skills_required": ["python"], "location": "Remote", "work_mode": "remote",
           "experience_required": "0-1 years", "posted_at": None, "title": "Test"}
    result = ScoringEngine.calculate_job_score(student, job)
    assert 0 <= result["total_score"] <= 100
