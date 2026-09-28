# Recruiter ATS Hiring Pipeline & Candidate Progression Design

## 1. Overview
The ATS (Applicant Tracking System) Hiring Pipeline provides recruiters with a unified visual Kanban board to manage candidates across customizable hiring stages (`Applied` → `Screening` → `Interview` → `Offer` → `Hired`/`Rejected`), perform drag-and-drop stage progression, review applicants using the 6-component Shared Fit Score in a slide-over review drawer, submit multi-criteria interview scorecards, and automatically keep students informed with real-time application milestones.

---

## 2. Real-World Problems Solved
1. **Recruiter Friction & Disorganization**: Eliminates clumsy spreadsheet/manual tracking by providing native drag-and-drop pipeline progression with optimistic UI feedback and automatic transition validation.
2. **Student "Black Hole"**: Keeps candidates engaged with real-time stage updates, structured feedback reasons, and clear milestone steps in their Application Tracker.
3. **Disconnected Screening & Evaluation**: Combines deterministic 6-component Shared Fit scoring, interviewer scorecards (Technical, Problem Solving, Communication, Culture), and direct interview proposal / offer creation in a single in-context slide-over drawer.

---

## 3. Architecture & Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Recruiter Workspace                             │
│                                                                        │
│  ┌────────────────────────┐         ┌────────────────────────────────┐ │
│  │ ApplicationPipeline    │ Drag &  │ ApplicationDetailDrawer        │ │
│  │ (Kanban Board)         │ Drop    │ - 6-Component Shared Fit Score │ │
│  │ 📥 Applied             │────────►│ - Stage History & Audit Trail  │ │
│  │ 🔍 Resume Screening    │         │ - Scorecard Form & Rollup      │ │
│  │ 🎙️ Phone Screen        │         │ - Interview / Offer Triggers   │ │
│  │ 💻 Technical Round     │         │ - Private Notes & Tags         │ │
│  │ 📝 Offer Extended      │         └────────────────────────────────┘ │
│  │ 🎉 Hired / ❌ Rejected  │                                            │
│  └────────────────────────┘                                            │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │ HTTP PATCH /move-stage & POST /scorecards
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend Services                           │
│                                                                        │
│  ┌────────────────────────┐         ┌────────────────────────────────┐ │
│  │ application_routes.py  │────────►│ outbox & background_scheduler │ │
│  │ - Stage Transition Auth│         │ - EventTypes.STAGE_CHANGED     │ │
│  │ - Transition Validator │         │ - Student In-App Notifications │ │
│  │ - Scorecard Rollup Calc│         │ - Calendar / Interview Sync    │ │
│  └────────────────────────┘         └────────────────────────────────┘ │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │ MongoDB Query
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Student Application Tracker                        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ApplicationTracker.jsx                                           │  │
│  │ - Milestone Tracker (Date, Time, Status, Stage Name, Next Action)│  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Component Specifications

### 4.1 Frontend Components
1. **`ApplicationPipeline.jsx` (Kanban Board)**:
   - Dynamic stage column rendering from active company pipeline template.
   - Native HTML5 Drag-and-Drop:
     - `draggable={true}` on candidate cards.
     - `onDragStart`: Captures `application_id`, source `stage_id`.
     - `onDragOver`: Highlights drop zone with subtle glow/border.
     - `onDrop`: Dispatches stage move with optimistic UI update.
     - Rollback on failure with toast error message.
   - Quick filters: search candidate by name/email, filter by fit score tier (>70% strong match, >40% moderate).
   - Candidate card summary: Name, initials avatar, applied date, fit score badge, quick advance / reject action buttons.
   - Clicking a card opens `ApplicationDetailDrawer`.

2. **`ApplicationDetailDrawer.jsx` (Slide-over Candidate Review Drawer)**:
   - **Header**: Candidate name, college, email, target job title, status badge, link to public profile.
   - **Tab 1: Fit & Profile**: Authoritative 6-component fit score breakdown (Skill Match 40%, Proficiency 20%, Freshness 15%, Location 10%, Career Alignment 10%, AI Readiness 5%) + matched & missing skills.
   - **Tab 2: Timeline & History**: Chronological stage movement log with timestamps and recruiter actor names.
   - **Tab 3: Scorecards (`ScorecardForm.jsx`)**:
     - Form to submit interview feedback: Technical Competence (1-5), Problem Solving (1-5), Communication (1-5), Culture Fit (1-5), Recommendation (`Strong Hire`, `Hire`, `No Hire`, `Strong No Hire`), Detailed Notes.
     - Average score computed and displayed as rollup on application card.
   - **Tab 4: Notes & Tags**: Private recruiter internal comments.
   - **Quick Actions Bar**:
     - "Propose / Schedule Interview" (triggers `InterviewModal`).
     - "Extend Offer" (triggers offer creation).
     - "Reject Application" (triggers stage move to `rejected` with reason prompt).

3. **`ApplicationTracker.jsx` (Student Milestone View)**:
   - Refined vertical milestone timeline with human-friendly date/time stamps.
   - Context-aware next action banner based on stage (e.g., "Interview proposal received — confirm your slot", "Technical assessment pending", "Offer extended — review terms").

---

## 5. Backend API & Transition Rules

### 5.1 Endpoints
- `GET /applications/board/{pipeline_id}/{job_id}`: Returns Kanban columns populated with candidates, candidate fit scores, and application tags.
- `PATCH /applications/{app_id}/move-stage`:
  - Body: `{"stage_id": str, "reason": Optional[str]}`
  - Validates recruiter owns the job/company.
  - Validates target `stage_id` belongs to active pipeline template.
  - Updates `current_stage_id`, `current_stage_name`, and appends to `stage_history`.
  - Creates outbox event `EventTypes.APPLICATION_STAGE_CHANGED`.
  - Emits in-app student notification.
- `POST /applications/{app_id}/scorecards`:
  - Body: `{"stage_id": str, "technical_score": int, "problem_solving_score": int, "communication_score": int, "culture_score": int, "recommendation": str, "notes": Optional[str]}`
  - Computes weighted overall score: `round(((tech + ps + comm + cult) / 20) * 100, 1)`.
  - Stores scorecard in `scorecards` collection / application document and updates `rating_summary`.

### 5.2 Transition Constraints
- Cannot move candidates out of terminal stages (`hired`, `rejected`, `withdrawn`).
- Rejection is valid from any non-terminal stage.
- Hired is valid when offer is accepted or directly advanced from offer stage.

---

## 6. Testing & Quality Assurance Plan
1. **Backend Integration Tests (`backend/tests/test_ats_pipeline_e2e.py`)**:
   - Verify pipeline board structure & candidate retrieval.
   - Test drag/drop stage transitions across all valid stages.
   - Test constraint enforcement (attempting invalid transitions from rejected/hired returns 400).
   - Test scorecard submission and overall score rollup calculation.
   - Test student application timeline visibility.
2. **Frontend Verification**:
   - Drag and drop simulation across columns.
   - Slide-over drawer opens, displays 6-component score, and submits scorecards.
   - Full Vite build check (`npm run build`).
