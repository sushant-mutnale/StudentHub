import pytest
from fastapi.testclient import TestClient

def test_student_analytics_access(authenticated_student_client: TestClient):
    """Test student getting their analytics overview."""
    response = authenticated_student_client.get("/analytics/student/overview")
    assert response.status_code == 200
    data = response.json()
    assert "applications" in data
    assert "recent_activity" in data
    assert data["applications"]["total"] >= 0

def test_recruiter_analytics_access(authenticated_recruiter_client: TestClient):
    """Test recruiter getting their analytics overview."""
    response = authenticated_recruiter_client.get("/analytics/recruiter/overview")
    assert response.status_code == 200
    data = response.json()
    assert "active_jobs" in data
    assert "total_applicants" in data
    assert "job_performance" in data

def test_student_cannot_access_recruiter_analytics(authenticated_student_client: TestClient):
    """Test student denied access to recruiter analytics."""
    response = authenticated_student_client.get("/analytics/recruiter/overview")
    assert response.status_code == 403

def test_recruiter_cannot_access_student_analytics(authenticated_recruiter_client: TestClient):
    """Test recruiter denied access to student analytics."""
    response = authenticated_recruiter_client.get("/analytics/student/overview")
    assert response.status_code == 403
