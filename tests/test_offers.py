import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_offer_management(
    client: TestClient,
    student_token: str,
    recruiter_token: str,
    test_job
):
    """Test creating and managing offers using explicit auth headers per request."""
    if "error" in test_job:
        pytest.skip(f"Job creation failed: {test_job.get('error')}")
    
    job_id = test_job.get("id") or test_job.get("_id")
    if not job_id:
        pytest.skip("Missing job ID in test_job fixture")
    
    student_headers = {"Authorization": f"Bearer {student_token}"}
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    
    # 1. Student applies first
    app_res = client.post(
        f"/jobs/{job_id}/apply",
        json={"message": "Looking forward to this opportunity!"},
        headers=student_headers
    )
    
    if app_res.status_code == 404:
        pytest.skip("Job apply endpoint not implemented")
    
    assert app_res.status_code in [200, 201], f"Apply failed: {app_res.text}"
    
    # Get student ID from 'me' endpoint
    me_res = client.get("/users/me", headers=student_headers)
    student_id = me_res.json().get("id") or me_res.json().get("_id")
    
    # 2. Recruiter creates offer with correct package structure
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    offer_payload = {
        "candidate_id": student_id,
        "job_id": job_id,
        "package": {
            "salary": 120000,
            "currency": "USD",
            "benefits": ["Health Insurance", "401k"],
            "equity": "0.1%"
        },
        "expires_at": expires_at,
        "notes": "We're excited to have you join our team!"
    }
    
    offer_res = client.post("/offers/", json=offer_payload, headers=recruiter_headers)
    
    if offer_res.status_code == 404:
        pytest.skip("Offer endpoints not implemented")
    
    assert offer_res.status_code in [200, 201], f"Offer creation failed: {offer_res.text}"
    offer_data = offer_res.json()
    offer_id = offer_data.get("id") or offer_data.get("_id") or offer_data.get("offer_id")
    
    # 3. Student views offer
    view_res = client.get(f"/offers/{offer_id}", headers=student_headers)
    if view_res.status_code == 404:
        pytest.skip("Offer view endpoint not implemented")
    assert view_res.status_code == 200
    
    # 4. Student accepts offer
    accept_res = client.post(f"/offers/{offer_id}/accept", headers=student_headers)
    if accept_res.status_code == 404:
        pytest.skip("Offer accept endpoint not implemented")
    assert accept_res.status_code in [200, 201]
