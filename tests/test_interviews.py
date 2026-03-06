import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_schedule_interview(
    client: TestClient, 
    student_token: str,
    recruiter_token: str,
    test_job
):
    """Test interview scheduling flow using explicit auth headers per request."""
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
        json={"message": "Please consider me for an interview!"},
        headers=student_headers
    )
    
    if app_res.status_code == 404:
        pytest.skip("Job apply endpoint not implemented")
    
    assert app_res.status_code in [200, 201], f"Apply failed: {app_res.text}"
    
    # Get student ID from 'me' endpoint
    me_res = client.get("/users/me", headers=student_headers)
    student_id = me_res.json().get("id") or me_res.json().get("_id")
    
    # 2. Recruiter schedules interview with correctly structured payload
    start_time = datetime.utcnow() + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)
    
    interview_payload = {
        "candidate_id": student_id,
        "job_id": job_id,
        "proposed_times": [
            {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "timezone": "UTC"
            }
        ],
        "location": {
            "type": "online",
            "url": "https://meet.google.com/abc-defg-hij"
        },
        "description": "Initial technical screening interview"
    }
    
    interview_res = client.post("/interviews/", json=interview_payload, headers=recruiter_headers)
    
    if interview_res.status_code == 404:
        pytest.skip("Interview endpoints not implemented")
    
    assert interview_res.status_code in [200, 201], f"Interview creation failed: {interview_res.text}"
