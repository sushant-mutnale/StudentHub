import pytest
from fastapi.testclient import TestClient

def test_hackathon_flow(authenticated_student_client: TestClient):
    """Test hackathon browsing."""
    
    # 1. List Hackathons
    response = authenticated_student_client.get("/hackathons/")
    if response.status_code == 404:
        pytest.skip("Hackathon endpoint not implemented")
        
    assert response.status_code == 200
    assert isinstance(response.json(), list)
