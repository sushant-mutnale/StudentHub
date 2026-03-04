# Detailed System Architecture & Data Flow Document

This document provides a comprehensive, detailed breakdown of the **StudentHub** platform's inner workings. It avoids strictly relying on UML files and instead uses deeply descriptive text flows (supported by standard markdown syntax) to analyze the entire system working, from the highest bird's-eye view down to the specific interactions inside each core module.

---

## 🏗️ 1. Overall System Architecture

The StudentHub platform operates on a modernized, decoupled architecture designed for AI integration and real-time processing.

### Components
1. **Frontend Client (React + Vite)**: 
   - SPA (Single Page Application) serving both Student and Recruiter roles through tailored dashboards.
   - Manages state using context and interacts with APIs via Axios interceptors.
2. **Backend Gateway & Core APIs (FastAPI)**:
   - High-performance, asynchronous Python backend handling JWT Authentication, business logic, and database transactions.
3. **Database Layer (MongoDB)**:
   - NoSQL structure allowing flexible schemas for User Profiles, Dynamic Assessments, and varied Job Postings.
4. **AI Engine Integration (Google Gemini LLM)**:
   - Injected deeply into the architecture to power features like the voice interview agent, resume grading, and automated profile matching.
5. **External Aggregators (Apify Scrapers)**:
   - Background workers pulling live jobs and hackathons from the internet (e.g., Internshala, Devpost) into the internal database.

---

## 🔄 2. Data Flow Diagrams (DFD)

### Level 0: Context Overview
The Level 0 DFD defines the absolute boundary of the system and how external entities interact with it.

- **Entity: Student**
  - **Data In:** Registration details, Resume (PDF/Text), Assessment answers, Voice interview audio inputs, Job applications.
  - **Data Out:** Formatted Resume UI, Personalized Learning Roadmaps, AI Interview Feedback/Scorecards, Recommended Jobs, Application Status Updates.
- **Entity: Recruiter**
  - **Data In:** Company details, Job Requirements, Interview prompts, Candidate stage movements (Kanban dragging), Candidate notes.
  - **Data Out:** Ranked lists of best-fit candidates, Candidate analytics, Direct chat messages from candidates.
- **Entity: External Web (Apify)**
  - **Data In:** Scraped Job URLs, External Hackathon descriptions.
- **System: StudentHub Core**
  - Sits in the middle, continuously transforming Student Resumes and Scraped Jobs into meaningful matches for the Recruiter.

---

### Level 1: Core Modular Breakdown
The system is divided into 5 distinct modules that pass data back and forth.

1. **User & Profile Management**
2. **Evaluation & Matching**
3. **Learning & Feedback**
4. **Recommendation & Notification**
5. **Communication & Tracking**

*Flow at Level 1:*
1. The Student inputs their raw profile into **Module 1**. 
2. **Module 1** parses the resume using AI and structured data is stored in DB.
3. **Module 2** routinely queries DB, comparing the Student's structured data against Job Postings from Recruiters.
4. When **Module 2** establishes to a high match score (>70%), it signals **Module 4**.
5. **Module 4** fires an alert to the Student's dashboard ("New Job Match!").
6. The Student engages with **Module 3** to take a skill test related to the job.
7. Upon passing, the Student applies, triggering **Module 5** to open a direct, trackable timeline between the Student and Recruiter.

---

### Level 2: Detailed Deep Dive Per Module

Here we zoom strictly into the specific, micro-level processes of the 5 Core Modules.

#### Module 1: User & Profile Management
- **Process 1.1: Authentication**: Accepts Email/Password or OAuth. Mints and returns a JWT Bearer token valid for active sessions.
- **Process 1.2: AI Resume Parsing**: 
  - *Input:* PDF Upload.
  - *Action:* OCR + LLM Extraction.
  - *Output:* JSON object containing normalized lists of Skills, Experience points, and Education.
- **Process 1.3: Recruiter Verification**: Admin-level manual or automated checks of company domains to mark a recruiter as "Verified."

#### Module 2: Evaluation & Matching
- **Process 2.1: Semantic Skill Mapping**: Uses the LLM to understand that "React.js" and "Frontend Developer" have high semantic correlation.
- **Process 2.2: The Scoring Engine**:
  - *Input:* Student Profile + Job Requirements.
  - *Action:* Calculates a base weight for matching skills, adds bonus weights for completed assessments and platform activity.
  - *Output:* A concrete `match_score` percentage (e.g., 85%).
- **Process 2.3: Ingestion Synchronization**: Background tasks (Cron jobs) executing Python scripts to pull Devpost/Internshala APIs, mapping them to the internal `Job` schema.

#### Module 3: Learning & Feedback
- **Process 3.1: Voice Interview Simulation**: 
  - *Input:* Text-to-Speech (TTS) prompts the user. User speaks into mic. Frontend captures base64 audio and sends to Backend. Speech-to-Text (STT) transcribes it.
  - *Action:* AI Agent analyzes transcripts in real-time.
- **Process 3.2: Scorecard Generation**:
  - *Action:* Following the interview, the AI assesses categories like "Technical Accuracy," "Communication," and "Confidence," generating a JSON scorecard.
- **Process 3.3: Dynamic Roadmap Creation**:
  - *Input:* Missing skills identified in the scorecard.
  - *Output:* Markdown-based learning path with generated milestones and YouTube/Web resource links.

#### Module 4: Recommendation & Notification
- **Process 4.1: Feed Generation**: The Opportunities UI calls the `/api/recommendations` endpoint. The backend sorts the opportunities DB by `match_score` DESC.
- **Process 4.2: Websocket / Polling Alerts**: In-app bell icon alerts.
  - *Triggers:* Status changes (e.g., "Application moved to Interview"), Platform messages, New highly compatible job posted.

#### Module 5: Communication & Tracking
- **Process 5.1: Kanban Pipeline Management**:
  - *Input:* Recruiter drags a candidate card from "Applied" to "Interview."
  - *Action:* Updates the `application.stage` field in MongoDB.
- **Process 5.2: Stage Timeline**:
  - *Output for Student:* Displays a vertical timeline (Applied -> Reviewed -> Interview -> Hired) marking the timestamp of every UI interaction the recruiter made.
- **Process 5.3: Integrated Messaging**: Facilitates direct Q&A between recruiters and approved candidates without them needing to exchange personal emails.

---

## 🎬 3. Detailed Sequence Flows

### Sequence A: The "Apply & Track" Flow
1. **[UI]** Student clicks "Apply" on a recommended Job posting.
2. **[Backend]** API validates if the Student profile meets hard constraints (if any).
3. **[Database]** Creates an `Application` document linking `student_id` and `job_id`, setting initial stage to `"Pending"`.
4. **[Backend]** Fires an internal system event to the Notification Service.
5. **[Database]** Saves an unread Notification for the Recruiter.
6. **[UI]** Recruiter logs in, sees the unread notification.
7. **[UI]** Recruiter opens the Pipeline Kanban board and views the new Applicant card.
8. **[Backend]** Recruiter updates the applicant's status to "Reviewed", triggering an immediate timeline update visible to the Student.

### Sequence B: The "AI Voice Interview" Flow
1. **[UI]** Student enters the "Interview Room" and grants Mic permissions.
2. **[Backend]** The `MasterAgent` orchestrates a greeting via Text-to-Speech service.
3. **[UI]** Student hears the greeting and speaks an answer.
4. **[UI -> Backend]** Raw audio is transmitted. 
5. **[Backend]** Audio is transcribed to text.
6. **[Backend -> LLM]** The system provides the transcription to the Gemini model along with the context of the job being interviewed for.
7. **[LLM -> Backend]** Gemini returns the next logical follow-up question.
8. **[Backend -> UI]** Question is converted back to voice and played for the student.
9. **[Backend]** Upon ending the call, the entire conversation history is analyzed to generate the `Scorecard` saving to the Database.
