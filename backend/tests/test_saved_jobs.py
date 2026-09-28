import pytest


@pytest.mark.asyncio
async def test_student_can_save_unsave_and_list_saved_jobs(
    client, recruiter_token, student_token
):
    # Create a job
    create_resp = await client.post(
        "/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "title": "Fullstack Intern",
            "description": "React and Node internship",
            "skills_required": ["React", "Node"],
            "location": "Hyderabad",
            "visibility": "public",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    headers = {"Authorization": f"Bearer {student_token}"}

    # Save
    save_resp = await client.post(f"/jobs/{job_id}/save", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["saved"] is True
    assert save_resp.json()["first_time"] is True

    # Saving again is idempotent (not "first_time")
    save2 = await client.post(f"/jobs/{job_id}/save", headers=headers)
    assert save2.status_code == 200
    assert save2.json()["first_time"] is False

    # List saved jobs
    saved_resp = await client.get("/jobs/saved", headers=headers)
    assert saved_resp.status_code == 200
    saved = saved_resp.json()
    assert any(j["id"] == job_id for j in saved)

    # Unsave
    unsave_resp = await client.delete(f"/jobs/{job_id}/save", headers=headers)
    assert unsave_resp.status_code == 204

    saved_after = await client.get("/jobs/saved", headers=headers)
    assert not any(j["id"] == job_id for j in saved_after.json())


@pytest.mark.asyncio
async def test_student_cannot_apply_to_same_job_twice(
    client, recruiter_token, student_token
):
    create_resp = await client.post(
        "/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "title": "Backend Intern",
            "description": "Python backend internship",
            "skills_required": ["Python"],
            "location": "Pune",
            "visibility": "public",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    headers = {"Authorization": f"Bearer {student_token}"}

    first = await client.post(
        f"/jobs/{job_id}/apply",
        headers=headers,
        json={"message": "Please consider my application"},
    )
    assert first.status_code == 201

    second = await client.post(
        f"/jobs/{job_id}/apply",
        headers=headers,
        json={"message": "Duplicate attempt"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "You have already applied to this job"
