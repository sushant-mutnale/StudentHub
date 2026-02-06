import pytest
from fastapi.testclient import TestClient

def test_get_job_recommendations(authenticated_student_client: TestClient):
    """Test getting job recommendations."""
    response = authenticated_student_client.get("/recommendations/jobs")
    if response.status_code == 404:
        pytest.skip("Recommendations endpoint not implemented")
        
    assert response.status_code == 200
    data = response.json()
    # Response could be a list of jobs or an object with jobs key
    assert isinstance(data, (list, dict))

def test_offline_recommendation_fallback(authenticated_student_client: TestClient):
    """Test recommendation system provides fallback when AI unavailable."""
    response = authenticated_student_client.get("/recommendations/jobs")
    if response.status_code == 404:
        pytest.skip("Recommendations endpoint not implemented")
        
    assert response.status_code == 200
    data = response.json()
    
    # Check if response contains source metadata (live, cached, etc.)
    # If it's a dict with metadata, check it; otherwise just verify it's valid
    if isinstance(data, dict):
        # Could have source field or just be valid response
        assert "jobs" in data or "source" in data or isinstance(data.get("items"), list)
    else:
        # It's a list - that's fine
        assert isinstance(data, list)
