# Student Hub – Full Stack Upgrade

Student Hub is now a full-stack platform that pairs a React 18 + Vite frontend (plain CSS, no Tailwind) with a FastAPI + MongoDB backend. Students post updates, manage rich profiles, and take assessments; recruiters publish roles and instantly discover matching candidates.

## 🚀 What's New

- **JWT Auth + FastAPI**: Login/signup now talk to a real Python backend with password hashing and JWT tokens.
- **MongoDB Schemas**: Users, posts, jobs, matches, messages, and assessments persist in MongoDB collections.
- **Public Profiles**: `/profile/:userId` renders a Twitter-style public profile with banner, PRN, skills, and personal feed.
- **Student Post Controls**: Students can edit/delete only their own posts and manage tags inline.
- **Recruiter Workspace**: Recruiters no longer see the student feed; they manage jobs and fetch skill-based matches per posting.
- **Messaging MVP**: Threaded inbox + conversations with unread counts, optimistic sends, and REST endpoints (`/threads`, `/threads/{id}`).
- **Interviews & Offers**: Recruiters can propose interviews, send offers, attach ICS invites, and track candidate responses with `/interviews` + `/offers` APIs.
- **Central API Client**: All React data comes from `src/api/client.js` via axios—no more localStorage mocks.

## 📁 Project Layout

```
D:\project\
 ├── backend/               # FastAPI + MongoDB backend
 │    ├── main.py           # FastAPI app + seeding + routers
 │    ├── config.py         # Settings via pydantic-settings
 │    ├── database.py       # Motor client + helpers
 │    ├── models/           # Mongo helpers (users, posts, jobs, messages, interviews, offers)
 │    ├── schemas/          # Pydantic models (auth, users, posts, jobs, threads, interviews, offers, etc.)
 │    ├── routes/           # FastAPI routers (auth, users, posts, jobs, matches, threads, interviews, offers)
 │    └── utils/            # Auth helpers, dependencies
 │
 └── frontend/              # React + Vite frontend
      ├── src/
      │    ├── api/client.js          # Axios base client + token handling
      │    ├── contexts/AuthContext.jsx
      │    ├── components/            # PublicProfile, StudentDashboard, RecruiterDashboard, PostFeed, etc.
      │    └── services/              # Thin wrappers over API endpoints
      ├── package.json
      ├── vite.config.js
      ├── index.html
      └── .env               # VITE_API_BASE_URL=http://127.0.0.1:8000
```

## ⚙️ Prerequisites

- **Frontend**: Node.js 18+ and npm
- **Backend**: Python 3.10+, MongoDB (local or Atlas)

## 🧪 Seed Accounts

On the first backend startup we seed two demo accounts:

- Student → `demo_student` / `Student@123`
- Recruiter → `demo_recruiter` / `Recruiter@123`

Use them to log in immediately, or create fresh users through the signup forms.

## 🔐 Environment Variables

### Backend

Create `backend/.env` with:

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=student_hub
JWT_SECRET=replace-with-a-long-random-string
FRONTEND_BASE_URL=http://localhost:5173  # preferred for link generation
FRONTEND_ORIGIN=http://localhost:5173    # legacy name still supported
APP_ENV=development
```

> Tip: copy/paste the block above and adjust for Atlas/production as needed.
- **Frontend base URL**: The backend constructs interview/offer links using `FRONTEND_BASE_URL` (preferred). If unset, it falls back to `FRONTEND_ORIGIN`, then `http://localhost:5173`. Set `FRONTEND_BASE_URL=https://app.studenthub.example.com` in production so emails carry the right domain.

### Frontend

Create `frontend/.env` with:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

This tells the React app where to find the backend API. The default fallback is `http://127.0.0.1:8000` if the env var is missing.

## 🛠️ Setup & Run

### Backend (FastAPI + MongoDB)

From the project root (`D:\project`):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

The API lives at `http://127.0.0.1:8000`. Swagger docs: `http://127.0.0.1:8000/docs`.

### Frontend (React + Vite)

From the project root (`D:\project`):

```bash
cd frontend
npm install
npm run dev
```

Vite serves the UI at `http://localhost:5173`. 

**Important**: Create `frontend/.env` file with the following content:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

This tells the React app where to find the backend API. Without this file, the frontend will still work (using the default `http://127.0.0.1:8000`), but it's best practice to have it explicitly set.

## 🔗 Key API Endpoints

- `POST /auth/signup/student` – includes PRN, skills, college data
- `POST /auth/signup/recruiter`
- `POST /auth/login` → `{ access_token, expires_at, user }`
- `GET /posts`, `POST /posts`, `PUT /posts/{id}`, `DELETE /posts/{id}`
- `GET /users/{id}` + `/users/{id}/posts` – powers the public profile route
- `POST /jobs`, `GET /jobs` (student/recruiter feed with filters), `GET /jobs/my`, `GET /jobs/{id}`, `DELETE /jobs/{id}`
- `GET /jobs/{jobId}/matches` – skill-intersection match list for recruiters
- `POST /threads` – create or reuse a thread (accepts participant ids or usernames, optional first message)
- `GET /threads` – inbox summary with per-user unread counts
- `GET /threads/{threadId}` – thread metadata + chronological, paginated messages
- `POST /threads/{threadId}/messages` – append a message, optimistic-safe
- `PUT /threads/{threadId}/read` – zero unread count + mark messages read
- `POST /interviews` – recruiter proposes an interview (timeslots + location)
- `GET /interviews/my` / `/interviews/{id}` – list + inspect interviews; accept/decline/reschedule/cancel/feedback endpoints live under `/interviews/{id}/*`
- `POST /offers` – recruiter sends an offer; `/offers/{id}` + `/offers/{id}/accept|reject|update` manage the lifecycle

All protected routes expect `Authorization: Bearer <token>`.

### Jobs API details

- `POST /jobs` (recruiter only):

  ```json
  {
    "title": "Java Developer - Intern",
    "description": "Looking for Java intern having basic knowledge of Spring Boot",
    "skills_required": ["Java", "Spring", "SQL"],
    "location": "Pune, India",
    "visibility": "public"
  }
  ```

- `GET /jobs` (students & recruiters):

  - **Query params**:
    - `q` – free-text search in `title` and `description`
    - `skills` – comma-separated skills (e.g. `Java,SQL`)
    - `location` – partial, case-insensitive match
    - `limit` – page size (default 20, max 100)
    - `skip` – offset for pagination
  - **Visibility rules**:
    - Students see only jobs where `visibility` is `public` or `students` (or not set, for legacy data).
    - Recruiters see their own jobs plus public/student-visible jobs.
  - **Response shape** (per item):

    ```json
    {
      "id": "64f0...",
      "recruiter_id": "64ef...",
      "title": "Java Developer - Intern",
      "description": "Looking for Java intern having basic knowledge of Spring Boot",
      "skills_required": ["Java", "Spring", "SQL"],
      "location": "Pune, India",
      "created_at": "2025-11-29T10:00:00.123Z",
      "visibility": "public",
      "company_name": "Talent Seekers"
    }
    ```

Example cURL calls:

```bash
# Create a job as recruiter (replace TOKEN with a recruiter JWT)
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "title": "Java Developer - Intern",
    "description": "Looking for Java intern having basic knowledge of Spring Boot",
    "skills_required": ["Java", "Spring", "SQL"],
    "location": "Pune, India",
    "visibility": "public"
  }'

# Fetch jobs as a student
curl "http://127.0.0.1:8000/jobs?q=java&skills=Java,SQL&limit=20" \
  -H "Authorization: Bearer TOKEN"
```

## 🧭 Frontend Highlights

- **AuthContext** stores JWT + user profile, refreshes via `/users/me`, and shares `signupStudent`, `signupRecruiter`, `logout`, and `refreshUser`.
- **PostFeed.jsx** fetches from `/posts`, offers inline edit/delete controls for the owner, displays tags, and links names/avatars to `/profile/:userId`.
- **PublicProfile.jsx** mirrors a Twitter profile with banner, stats, PRN (students), company details (recruiters), skill chips, and that user’s posts.
- **RecruiterDashboard.jsx** focuses solely on job management + “View Matching Students” per posting, hiding the global student feed entirely.
- **Inbox / Conversation** pages show threads, unread badges, optimistic composer, and call the new `/threads` APIs through `messageService.js`.
- **Interviews / Offers pages** (WIP) consume the `/interviews` and `/offers` APIs. Recruiters can propose slots, send offers, and candidates can accept/decline directly from the UI or via the thread cards.

## ✅ Testing Checklist

1. **Start MongoDB** (if running locally):
   ```bash
   mongod
   ```

2. **Start Backend** (Terminal 1):
   ```bash
   cd D:\project\backend
   .venv\Scripts\activate
   uvicorn backend.main:app --reload
   ```

3. **Start Frontend** (Terminal 2):
   ```bash
   cd D:\project\frontend
   npm run dev
   ```

4. **Test Login**:
   - Open `http://localhost:5173` in your browser
   - Login as `demo_student` / `Student@123`
   - If you see "Network Error", check:
     - Backend is running at `http://127.0.0.1:8000`
     - `frontend/.env` has `VITE_API_BASE_URL=http://127.0.0.1:8000`
     - Browser console shows detailed error logs (not just "Network Error")

5. **Test Features**:
   - Create a post with tags, then edit & delete it
   - Visit your own `@handle` to confirm the public profile
   - Login as `demo_recruiter` / `Recruiter@123`
   - Post a new job with several skills
   - Click "View Matching Students" to see ranked candidates
   - Open `/messages`, start a thread (e.g., student ↔ recruiter), send a few messages
   - Refresh the page and/or login as the other account to confirm unread badges increment and `PUT /threads/{id}/read` clears them
   - From the recruiter account, call `POST /interviews` (Swagger) to propose a slot against the student, then login as the student to call `/interviews/{id}/accept` or `/decline`. Confirm a notification document, thread message, and (if configured) email/ICS invite were produced.
   - Exercise `/interviews/{id}/reschedule`, `/cancel`, and `/feedback` to verify history tracking.
   - Use `POST /offers` as the recruiter to send a package; as the student, hit `/offers/{id}/accept` or `/reject`. Recruiter can `PUT /offers/{id}` to withdraw/update and should see updated history + notifications.

### Interview proposal field reference

When calling `POST /interviews` (either via Swagger or the recruiter UI):

- `candidate_id` **must** be the MongoDB ObjectId string for the candidate user (e.g. `66c5...`). Usernames are not accepted here—look up the candidate via `/users` or copy the `_id` from MongoDB/Swagger first.
- `job_id` is optional and should also be an ObjectId string if you want to link the interview to a job posting.
- `thread_id` is optional and expects the thread’s ObjectId string; when provided, the API posts an interview card message into that thread automatically.
- `proposed_times` is an array of `{ start, end, timezone }` objects where `start/end` are ISO datetimes (e.g. `2025-12-01T15:00:00Z`) and `timezone` is an Olson tz string such as `UTC` or `America/New_York`.
- `location` requires `{ type: "online"|"onsite", url?, address? }` — supply `url` for `online` or `address` for `onsite`.
- `description` is free text for the agenda/notes (optional, but gets sanitized server-side).

## 📦 Production Builds

- **Frontend**: `npm run build` → `dist/`
- **Backend**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`

Deploy them behind HTTPS + a managed MongoDB instance for best results.

---

Happy hacking with Student Hub 2.0! 🎓💼


