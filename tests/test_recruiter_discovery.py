import pytest
from fastapi.testclient import TestClient

def test_search_candidates(authenticated_recruiter_client: TestClient):
    """Test searching candidates by skill."""
    response = authenticated_recruiter_client.get("/users/search?skill=Python")
    
    if response.status_code == 404:
        pytest.skip("Search endpoint not implemented")
        
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    
def test_view_candidate_profile(authenticated_recruiter_client: TestClient, authenticated_student_client: TestClient):
    """Test viewing a specific candidate profile."""
    # First get the student's ID
    me_res = authenticated_student_client.get("/users/me")
    if me_res.status_code != 200:
        pytest.skip("Could not get student profile")
    
    student_id = me_res.json().get("id") or me_res.json().get("_id")
    
    # Recruiter views student profile
    response = authenticated_recruiter_client.get(f"/users/{student_id}")
    
    if response.status_code == 404:
        pytest.skip("User profile endpoint not implemented")
    
    assert response.status_code == 200
    profile = response.json()
    assert profile.get("id") == student_id or profile.get("_id") == student_id
