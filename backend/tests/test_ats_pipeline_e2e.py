"""
E2E test for ATS Pipeline: job post → apply → stage transition → scorecard → board.
Tests real HTTP endpoints via the FastAPI test client.
"""

import pytest
from bson import ObjectId


@pytest.mark.asyncio
async def test_ats_pipeline_and_scorecard_lifecycle(client, recruiter_token, student_token):
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Post a job (recruiter)
    job_payload = {
        "title": "Full Stack Engineer",
        "description": "FastAPI + React engineering.",
        "skills_required": ["Python", "React", "MongoDB"],
        "location": "Remote",
    }
    job_resp = await client.post("/jobs/", json=job_payload, headers=recruiter_headers)
    assert job_resp.status_code == 201, f"Job creation failed: {job_resp.text}"
    job_id = job_resp.json()["id"]

    # 2. Student applies
    apply_resp = await client.post(
        f"/jobs/{job_id}/apply",
        json={"message": "Excited to apply!"},
        headers=student_headers,
    )
    assert apply_resp.status_code == 201, f"Apply failed: {apply_resp.text}"

    # 3. Get recruiter applications for this job
    apps_resp = await client.get(f"/applications/job/{job_id}", headers=recruiter_headers)
    assert apps_resp.status_code == 200, f"List applications failed: {apps_resp.text}"
    apps_data = apps_resp.json()
    assert apps_data["total"] >= 1
    app_id = apps_data["applications"][0]["id"]

    # 4. Get active pipeline to find a later stage (screening or interview)
    pipeline_resp = await client.get("/pipelines/active", headers=recruiter_headers)
    assert pipeline_resp.status_code == 200, f"Get active pipeline failed: {pipeline_resp.text}"
    pipeline = pipeline_resp.json()
    pipeline_id = pipeline["id"]
    stages = pipeline["stages"]

    # Find a stage after "Applied" - prefer screening, then interview
    applied_stage = next(s for s in stages if s["type"] == "applied")
    screening_stage = next((s for s in stages if s["type"] == "screening"), None)
    interview_stage = next((s for s in stages if s["type"] == "interview"), None)

    # Pick target stage: screening if available, else first interview
    target_stage = screening_stage or interview_stage
    assert target_stage is not None, "No screening or interview stage found in pipeline"
    target_stage_id = target_stage["id"]

    # 5. Move stage to target stage (PUT /applications/{app_id}/stage)
    move_resp = await client.put(
        f"/applications/{app_id}/stage",
        json={"new_stage_id": target_stage_id, "reason": "Strong profile fit"},
        headers=recruiter_headers,
    )
    assert move_resp.status_code == 200, f"Stage move failed: {move_resp.text}"
    moved_app = move_resp.json()
    assert moved_app["current_stage_id"] == target_stage_id

    # 6. Get scorecard templates (auto-creates defaults if none)
    templates_resp = await client.get("/scorecards/templates", headers=recruiter_headers)
    assert templates_resp.status_code == 200, f"Get templates failed: {templates_resp.text}"
    templates_data = templates_resp.json()
    assert templates_data["total"] > 0

    # Find a template matching the current stage type
    matching_templates = [t for t in templates_data["templates"] if t["stage_type"] == target_stage["type"]]
    assert matching_templates, f"No template for stage type {target_stage['type']}"
    template = matching_templates[0]
    template_id = template["id"]

    # 7. Submit scorecard with high scores (4-5) to achieve overall_score >= 80
    # Criteria names from template
    criteria_names = [c["name"] for c in template["criteria"]]
    scores_payload = [
        {"criterion": name, "score": 5, "notes": "Excellent"}
        for name in criteria_names
    ]
    scorecard_payload = {
        "template_id": template_id,
        "stage_id": target_stage_id,
        "scores": scores_payload,
        "decision": "pass",
        "overall_notes": "Strong hire",
    }
    sc_resp = await client.post(
        f"/scorecards/applications/{app_id}",
        json=scorecard_payload,
        headers=recruiter_headers,
    )
    assert sc_resp.status_code == 201, f"Scorecard submission failed: {sc_resp.text}"
    scorecard = sc_resp.json()
    assert scorecard["overall_score"] >= 4.0, f"Expected overall_score >= 4.0, got {scorecard['overall_score']}"

    # 8. Verify pipeline board shows candidate in correct stage column
    board_resp = await client.get(f"/pipelines/{pipeline_id}/board/{job_id}", headers=recruiter_headers)
    assert board_resp.status_code == 200, f"Get board failed: {board_resp.text}"
    board = board_resp.json()
    assert board["total_candidates"] >= 1

    # Find the column matching target stage
    target_column = next((c for c in board["columns"] if c["stage_id"] == target_stage_id), None)
    assert target_column is not None, f"Stage column {target_stage_id} not found on board"
    candidate_in_column = next((c for c in target_column["candidates"] if c["application_id"] == app_id), None)
    assert candidate_in_column is not None, f"Application {app_id} not found in stage {target_stage['name']}"
    assert candidate_in_column["overall_score"] is not None
    # Score is reflected as 0-5 scale (raw average of criterion scores)
    assert candidate_in_column["overall_score"] >= 4.0


@pytest.mark.asyncio
async def test_stage_move_and_scorecard_authz(client, recruiter_token, student_token):
    """Verify authorization: student cannot move stage or submit scorecard."""
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Create a job and apply as student
    job_payload = {
        "title": "Backend Engineer",
        "description": "Python backend role.",
        "skills_required": ["Python", "FastAPI"],
        "location": "Remote",
    }
    job_resp = await client.post("/jobs/", json=job_payload, headers=recruiter_headers)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    apply_resp = await client.post(
        f"/jobs/{job_id}/apply",
        json={"message": "I want this job"},
        headers=student_headers,
    )
    assert apply_resp.status_code == 201

    # Get the application
    apps_resp = await client.get(f"/applications/job/{job_id}", headers=recruiter_headers)
    apps_data = apps_resp.json()
    app_id = apps_data["applications"][0]["id"]

    # Get active pipeline
    pipeline_resp = await client.get("/pipelines/active", headers=recruiter_headers)
    pipeline = pipeline_resp.json()
    pipeline_id = pipeline["id"]
    stages = pipeline["stages"]

    screening_stage = next((s for s in stages if s["type"] == "screening"), None)
    assert screening_stage
    screening_stage_id = screening_stage["id"]

    # Student tries to move stage -> should be 403 (student not authorized for PUT /applications/{id}/stage)
    move_resp = await client.put(
        f"/applications/{app_id}/stage",
        json={"new_stage_id": screening_stage_id, "reason": "Trying to move"},
        headers=student_headers,
    )
    assert move_resp.status_code == 403, f"Expected 403 for student moving stage, got {move_resp.status_code}"

    # Student tries to submit scorecard -> should be 403
    templates_resp = await client.get("/scorecards/templates", headers=recruiter_headers)
    templates_data = templates_resp.json()
    template = next(t for t in templates_data["templates"] if t["stage_type"] == "screening")
    template_id = template["id"]
    criteria_names = [c["name"] for c in template["criteria"]]
    scores_payload = [{"criterion": name, "score": 5, "notes": "Test"} for name in criteria_names]
    scorecard_payload = {
        "template_id": template_id,
        "stage_id": screening_stage_id,
        "scores": scores_payload,
        "decision": "pass",
        "overall_notes": "Test",
    }
    sc_resp = await client.post(
        f"/scorecards/applications/{app_id}",
        json=scorecard_payload,
        headers=student_headers,
    )
    assert sc_resp.status_code == 403, f"Expected 403 for student submitting scorecard, got {sc_resp.status_code}"

    # Student tries to access board -> should be 403 (recruiter only endpoint)
    board_resp = await client.get(f"/pipelines/{pipeline_id}/board/{job_id}", headers=student_headers)
    assert board_resp.status_code == 403, f"Expected 403 for student accessing board, got {board_resp.status_code}"