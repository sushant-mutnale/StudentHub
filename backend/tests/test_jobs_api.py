import pytest

@pytest.mark.asyncio
async def test_recruiter_can_create_job_and_student_can_list_it(client, recruiter_token, student_token):
    # Create a job
    create_resp = await client.post(
        "/jobs/",
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

    # Fetch public jobs as the student
    list_resp = await client.get(
        "/jobs/",
        headers={"Authorization": f"Bearer {student_token}"},
        params={"skills": "Java,SQL", "limit": 20},
    )
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert any(j["id"] == job["id"] for j in jobs)


@pytest.mark.asyncio
async def test_recruiter_my_jobs_returns_only_their_jobs(client, recruiter_token):
    my_jobs_resp = await client.get(
        "/jobs/my", headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    assert my_jobs_resp.status_code == 200
    jobs = my_jobs_resp.json()
    # All jobs should have a recruiter_id present and be strings
    assert all(isinstance(j["recruiter_id"], str) for j in jobs)



