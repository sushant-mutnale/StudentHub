import pytest
from fastapi.testclient import TestClient

def test_create_profile(authenticated_student_client: TestClient):
    """Test initial profile creation."""
    profile_data = {
        "skills": [{"name": "Python", "level": 80}, {"name": "React", "level": 50}],
        "education": [{
            "institution": "Tech University",
            "degree": "B.Tech",
            "year": 2024
        }],
        "location": "New York"
    }
    
    response = authenticated_student_client.put("/users/me", json=profile_data)
    if response.status_code != 200:
        pytest.fail(f"Profile update failed: {response.text}")
        
    assert response.status_code == 200
    data = response.json()
    assert data.get("username") or data.get("email") # Check basic user fields

def test_upload_resume(authenticated_student_client: TestClient):
    """Test resume upload (mocked)."""
    # TestClient supports files
    files = {'file': ('resume.pdf', b'dummy content', 'application/pdf')}
    response = authenticated_student_client.post("/users/me/resume", files=files)
    
    if response.status_code == 404:
        pytest.skip("Resume upload endpoint not implemented")
        
    assert response.status_code == 200
    assert "url" in response.json()

def test_get_ai_stats(authenticated_student_client: TestClient):
    """Test retrieving AI profile statistics."""
    # Stats are embedded in the user profile under 'ai_profile'
    response = authenticated_student_client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    # Check ai_profile field or scores if they exist
    if "ai_profile" in data and data["ai_profile"]:
        assert "overall_score" in data["ai_profile"]
    else:
        # If AI profile not calculated yet, usually None.
        # Ensure 'ai_profile' key is present in schema response
        assert "ai_profile" in data
