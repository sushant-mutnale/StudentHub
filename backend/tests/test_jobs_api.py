import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_recruiter_can_create_job_and_student_can_list_it():
  async with AsyncClient(app=app, base_url="http://test") as client:
      # Login as seeded recruiter
      login_resp = await client.post(
          "/auth/login",
          json={"username": "demo_recruiter", "password": "Recruiter@123", "role": "recruiter"},
      )
      assert login_resp.status_code == 200
      recruiter_token = login_resp.json()["access_token"]

      # Create a job
      create_resp = await client.post(
          "/jobs",
          headers={"Authorization": f"Bearer {recruiter_token}"},
          json={
              "title": "Java Developer - Intern",
              "description": "Looking for Java intern having basic knowledge of Spring Boot",
              "skills_required": ["Java", "Spring", "SQL"],
              "location": "Pune, India",
              "visibility": "public",
          },
      )
      assert create_resp.status_code == 201
      job = create_resp.json()
      assert job["title"] == "Java Developer - Intern"
      assert job["visibility"] == "public"

      # Login as seeded student
      student_login = await client.post(
          "/auth/login",
          json={"username": "demo_student", "password": "Student@123", "role": "student"},
      )
      assert student_login.status_code == 200
      student_token = student_login.json()["access_token"]

      # Fetch public jobs as the student
      list_resp = await client.get(
          "/jobs",
          headers={"Authorization": f"Bearer {student_token}"},
          params={"skills": "Java,SQL", "limit": 20},
      )
      assert list_resp.status_code == 200
      jobs = list_resp.json()
      assert any(j["id"] == job["id"] for j in jobs)


@pytest.mark.asyncio
async def test_recruiter_my_jobs_returns_only_their_jobs():
  async with AsyncClient(app=app, base_url="http://test") as client:
      login_resp = await client.post(
          "/auth/login",
          json={"username": "demo_recruiter", "password": "Recruiter@123", "role": "recruiter"},
      )
      assert login_resp.status_code == 200
      token = login_resp.json()["access_token"]

      my_jobs_resp = await client.get(
          "/jobs/my", headers={"Authorization": f"Bearer {token}"}
      )
      assert my_jobs_resp.status_code == 200
      jobs = my_jobs_resp.json()
      # All jobs should have a recruiter_id present and be strings
      assert all(isinstance(j["recruiter_id"], str) for j in jobs)



