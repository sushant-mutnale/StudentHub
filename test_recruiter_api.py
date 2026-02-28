import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def run_test():
    run_id = str(uuid.uuid4())[:8]
    print(f"--- Starting E2E Recruiter Tests (Run ID: {run_id}) ---")

    # 1. Login Recruiter (Use seeded default user)
    print("\n1. Logging in Recruiter")
    rec_payload = {
        "username": "demo_recruiter",
        "password": "Recruiter@123",
        "role": "recruiter"
    }
    res = requests.post(f"{BASE_URL}/auth/login", json=rec_payload)
    assert res.status_code == 200, f"Recruiter login failed: {res.text}"
    rec_token = res.json().get("access_token")
    rec_headers = {"Authorization": f"Bearer {rec_token}"}
    print("✓ Recruiter Logged In")

    # 2. Create Job
    print("\n2. Creating Job")
    job_payload = {
        "title": "Senior Frontend Developer",
        "description": "Looking for a React expert with Tailwind experience.",
        "skills_required": ["React", "JavaScript", "Tailwind"],
        "location": "Remote",
        "job_type": "Full-time",
        "experience_level": "Senior"
    }
    res = requests.post(f"{BASE_URL}/jobs/", json=job_payload, headers=rec_headers)
    assert res.status_code in [200, 201], f"Job creation failed (Status: {res.status_code}): {res.text}"
    job_id = res.json().get("id")
    print(f"✓ Job Created (ID: {job_id})")

    # 3. Login Student (Use seeded default user)
    print("\n3. Logging in Student")
    student_payload = {
        "username": "demo_student",
        "password": "Student@123",
        "role": "student"
    }
    res = requests.post(f"{BASE_URL}/auth/login", json=student_payload)
    assert res.status_code == 200, f"Student login failed: {res.text}"
    student_token = res.json().get("access_token")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("✓ Student Logged In")

    # 4. Student updates profile to match skills
    print("\n4. Updating Student Profile")
    profile_payload = {
        "skills": [{"name": "React", "level": 80, "proficiency": "Advanced"}, {"name": "JavaScript", "level": 90, "proficiency": "Expert"}],
        "bio": "I love frontend."
    }
    res = requests.put(f"{BASE_URL}/users/me", json=profile_payload, headers=student_headers)
    assert res.status_code == 200, f"Student profile update failed: {res.text}"
    print("✓ Student Profile Updated")

    # 5. Student Applies for Job
    print("\n5. Applying for Job")
    app_payload = {
        "job_id": job_id,
        "resume_id": "test_resume_url",
        "message": "I would love to apply for this job."
    }
    res = requests.post(f"{BASE_URL}/jobs/{job_id}/apply", json=app_payload, headers=student_headers)
    # 400 means already applied or similar, but 200 is success. 201 could be success. 
    assert res.status_code in [200, 201], f"Application failed (Status {res.status_code}): {res.text}"
    app_id = res.json().get("id") or res.json().get("application_id")
    student_id = res.json().get("student_id")
    print(f"✓ Application Created (ID: {app_id}, Student ID: {student_id})")

    # 6. Recruiter Pipeline Board Check
    print("\n6. Checking Pipeline")
    res = requests.get(f"{BASE_URL}/pipelines", headers=rec_headers)
    assert res.status_code == 200, f"Get pipelines failed: {res.text}"
    pipelines_res = res.json()
    pipelines = pipelines_res.get("pipelines", [])
    if not pipelines:
        print("  ! Creating default pipeline since none exists")
        res = requests.post(f"{BASE_URL}/pipelines", json={"name": "Standard Hiring Pipeline"}, headers=rec_headers)
        assert res.status_code in [200, 201], f"Pipeline creation failed: {res.text}"
        pipeline_id = res.json().get("id")
    else:
        pipeline_id = pipelines[0]["_id"] if "_id" in pipelines[0] else pipelines[0]["id"]
    
    res = requests.get(f"{BASE_URL}/pipelines/{pipeline_id}/board/{job_id}", headers=rec_headers)
    assert res.status_code == 200, f"Get pipeline board failed: {res.text}"
    board = res.json()
    assert board and "columns" in board, "Invalid board structure"
    # Find candidate in applied column
    found = False
    for col in board.get("columns", []):
        for cand in col.get("candidates", []):
            if cand.get("student_id") == student_id:
                found = True
                print(f"✓ Found candidate in pipeline stage: {col.get('stage_name')}")
    assert found, "Candidate missing from pipeline board"

    # 7. Recruiter Analytics
    print("\n7. Checking Recruiter Analytics Overview")
    res = requests.get(f"{BASE_URL}/analytics/recruiter/overview", headers=rec_headers)
    assert res.status_code == 200, f"Analytics overview failed: {res.text}"
    analytics = res.json()
    print("✓ Analytics Overview Data:")
    print(json.dumps(analytics, indent=2))
    assert analytics.get("total_applicants", 0) >= 1, "Analytics missing the test applicant"

    print("\n8. Checking Recruiter Job Funnel")
    res = requests.get(f"{BASE_URL}/analytics/recruiter/job/{job_id}/funnel", headers=rec_headers)
    assert res.status_code == 200, f"Analytics job funnel failed: {res.text}"
    funnel = res.json()
    print("✓ Job Funnel Data:")
    print(json.dumps(funnel, indent=2))

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    run_test()
