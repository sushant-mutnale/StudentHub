# ATS Hiring Pipeline & Candidate Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Recruiter ATS Hiring Pipeline with native drag-and-drop Kanban, a candidate review slide-over drawer featuring the 6-component Shared Fit score, interviewer scorecards with rollup ratings, and real-time student milestone tracking.

**Architecture:** Native HTML5 Drag-and-Drop Kanban in `ApplicationPipeline.jsx` communicates with FastAPI `application_routes.py` for atomic stage transitions with transactional outbox events. An in-context slide-over drawer (`ApplicationDetailDrawer.jsx`) displays the 6-component Shared Fit Score, stage history, and interviewer scorecards (`ScorecardForm.jsx`), while `ApplicationTracker.jsx` keeps students updated in real-time.

**Tech Stack:** React (Vite, CSS Modules / App.css), FastAPI, MongoDB (Motor), Redis, Pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-ats-hiring-pipeline-design.md`

## Global Constraints
- All backend stage moves must validate against active pipeline template constraints.
- Fit scores must strictly use the authoritative 0–100 scale from `ScoringEngine` / `fit_scoring.py`.
- No external heavy drag-and-drop npm dependencies (use native HTML5 drag-and-drop API).
- All student status changes must emit structured outbox events and in-app notifications.

---

### Task 1: Backend Scorecard Rollup & Stage Movement API Enhancements

**Files:**
- Modify: `backend/routes/application_routes.py`
- Modify: `backend/models/application.py`
- Create: `backend/tests/test_ats_pipeline_e2e.py`

**Interfaces:**
- Consumes: `get_current_recruiter`, `pipeline_model.get_active_pipeline`
- Produces: `POST /applications/{app_id}/scorecards`, `PATCH /applications/{app_id}/move-stage`, `GET /applications/board/{pipeline_id}/{job_id}`

- [ ] **Step 1: Write the failing E2E test for stage transitions and scorecards**

Write `backend/tests/test_ats_pipeline_e2e.py`:
```python
import pytest
from bson import ObjectId

@pytest.mark.asyncio
async def test_ats_pipeline_and_scorecard_lifecycle(client, recruiter_token, student_token):
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Post a job
    job_payload = {
        "title": "Full Stack Engineer",
        "description": "FastAPI + React engineering.",
        "skills_required": ["Python", "React", "MongoDB"],
        "location": "Remote",
    }
    job_resp = await client.post("/jobs/", json=job_payload, headers=recruiter_headers)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 2. Student applies
    apply_resp = await client.post(
        f"/jobs/{job_id}/apply",
        json={"message": "Excited to apply!"},
        headers=student_headers,
    )
    assert apply_resp.status_code == 201

    # 3. Get recruiter applications
    apps_resp = await client.get(f"/applications/recruiter/job/{job_id}", headers=recruiter_headers)
    assert apps_resp.status_code == 200
    apps_data = apps_resp.json()
    assert apps_data["total"] >= 1
    app_id = apps_data["applications"][0]["id"]

    # 4. Move stage to screening / interview
    move_resp = await client.patch(
        f"/applications/{app_id}/move-stage",
        json={"stage_name": "Resume Screening", "reason": "Strong profile fit"},
        headers=recruiter_headers,
    )
    assert move_resp.status_code in [200, 204]

    # 5. Submit interviewer scorecard
    scorecard_payload = {
        "technical_score": 4,
        "problem_solving_score": 5,
        "communication_score": 4,
        "culture_score": 5,
        "recommendation": "Strong Hire",
        "notes": "Excellent algorithmic and communication skills.",
    }
    sc_resp = await client.post(
        f"/applications/{app_id}/scorecards",
        json=scorecard_payload,
        headers=recruiter_headers,
    )
    assert sc_resp.status_code == 201
    assert sc_resp.json()["overall_score"] >= 80.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ats_pipeline_e2e.py -v`
Expected: FAIL (endpoint or parameter mismatch)

- [ ] **Step 3: Implement scorecard submission & stage transition enhancements in backend**

Update `backend/routes/application_routes.py` with the scorecard submission endpoint and stage transition helper.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ats_pipeline_e2e.py -v`
Expected: PASS

---

### Task 2: Drag-and-Drop Kanban Board Enhancement

**Files:**
- Modify: `frontend/src/components/ApplicationPipeline.jsx`
- Modify: `frontend/src/services/pipelineService.js`
- Modify: `frontend/src/services/applicationService.js`

**Interfaces:**
- Consumes: `applicationService.moveStage`, `pipelineService.getPipelineBoard`
- Produces: HTML5 DnD event handlers (`handleDragStart`, `handleDragOver`, `handleDrop`, `handleCardClick`)

- [ ] **Step 1: Update `ApplicationPipeline.jsx` with native HTML5 Drag-and-Drop handlers**

Add:
- `onDragStart={(e) => handleDragStart(e, candidate, stage.stage_id)}`
- `onDragOver={(e) => handleDragOver(e, stage.stage_id)}`
- `onDragLeave={(e) => handleDragLeave(e, stage.stage_id)}`
- `onDrop={(e) => handleDrop(e, stage.stage_id)}`
- Visual dragging styling (dashed border, active background tint, drop target animation).
- Optimistic card movement with state rollback on error.
- Search input filter by candidate name or skill.

---

### Task 3: Application Detail Slide-Over Drawer Component

**Files:**
- Create: `frontend/src/components/ApplicationDetailDrawer.jsx`
- Modify: `frontend/src/components/ApplicationPipeline.jsx`

**Interfaces:**
- Consumes: `ScorecardForm.jsx`, `InterviewModal.jsx`, `fit_scoring` API
- Produces: `<ApplicationDetailDrawer isOpen={drawerOpen} candidate={activeCandidate} onClose={closeDrawer} />`

- [ ] **Step 1: Implement `ApplicationDetailDrawer.jsx`**

Create slide-over drawer with:
1. Header: Candidate avatar, full name, email, target job title, status badge, link to public profile.
2. 4 Tabs:
   - **Fit & Profile**: 6-component Shared Fit score breakdown (`Skill Match`, `Proficiency Fit`, `Freshness`, `Location`, `Career Alignment`, `AI Readiness`) + Matched/Missing skills pills.
   - **Timeline**: Stage history timeline with timestamps and actors.
   - **Scorecards**: Embedded `ScorecardForm` allowing interview rating submission (Technical, Problem Solving, Communication, Culture) + display of submitted scorecards.
   - **Notes & Tags**: Recruiter private notes with add note form.
3. Quick action bar: "Schedule Interview", "Extend Offer", "Reject Application".

- [ ] **Step 2: Integrate `ApplicationDetailDrawer` into `ApplicationPipeline.jsx`**

Render drawer conditionally and connect card clicks to open the drawer.

---

### Task 4: Student Application Tracker Milestone Sync

**Files:**
- Modify: `frontend/src/components/ApplicationTracker.jsx`

**Interfaces:**
- Consumes: `applicationService.getStudentApplications`
- Produces: Contextual next-action milestone banner and real-time status tracker.

- [ ] **Step 1: Enhance `ApplicationTracker.jsx`**

Add stage-specific next-action guidance cards:
- Applied: "Application received — our team is reviewing your profile."
- Screening / Interview: "Interview round active — prepare using our AI Mock Interviewer."
- Offer Extended: "Congratulations! An offer has been extended — review details."
- Hired: "Welcome aboard! 🎉"

---

### Task 5: Full Verification & Build Check

**Files:**
- Run: `backend/tests/test_ats_pipeline_e2e.py`
- Run: Frontend build `npm run build`

- [ ] **Step 1: Run backend pytest suite**
Run: `$env:MONGODB_URI="mongodb://localhost:27017"; $env:REDIS_URL="redis://127.0.0.1:6380"; & .\venv\Scripts\python.exe -m pytest backend/tests/test_ats_pipeline_e2e.py -v`
Expected: 100% PASS

- [ ] **Step 2: Run frontend production build**
Run: `npm run build` (in `frontend/`)
Expected: Clean build without errors
