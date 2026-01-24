Where it fits in StudentHub
Your current system already has the real recruitment flow: matching → messaging → interview scheduling → offer.
​

The AI simulator is the practice version of recruitment, which belongs to the “continuous improvement” loop (skill gaps → practice → evaluation → updated profile).
​

So: Module 3 = Learning & Feedback + AI Interview Preparation (MVP first, then advanced).
​

What exists & what’s missing (validated quickly)
Pramp is peer-to-peer mock interviewing (human-dependent, not scalable for everyone 24/7).
​

Interviewing.io focuses on realistic mocks with experienced interviewers and is not designed as a free college-scale simulator.

Your gap/opportunity is exactly what you wrote: “company + role + resume + adaptive flow + reusable knowledge”.

How to implement this inside Module 3 (practical plan)
A) Split Module 3 into 3 parts
Skill Gap + Learning Path (already discussed)

AI Interview Simulator (Recruitment Practice Engine) ← new submodule

Feedback + Memory Loop (stores everything and updates AI Career Profile)

This keeps your architecture clean and still “5 modules” overall.

Module 3B: AI Interview Simulator (MVP → Advanced)
MVP (build this first, 2–3 weeks)
Goal: one complete simulated interview flow, even if company research is basic.

Inputs (student provides)

Resume text (initially paste text, later PDF upload)

Target role (e.g., SDE Intern / Backend Intern)

Job description text (need to implement this also in MVP)

Company name (need to implement this also in MVP)

Rounds (MVP)

Round 1: DSA coding round (timer + hidden/public tests)

Round 2: Resume-based technical Q&A (projects, skills, decisions)

Round 3: Behavioral STAR (generic at first)

Evaluation (MVP)

Coding: correctness by testcases + time limit

Q&A + Behavioral: rubric scoring (clarity, depth, structure), plus LLM feedback (Gemini free-tier is enough)

Storage (MVP)

Save every attempt so it becomes reusable and improves future sessions:

interview_attempts

question_bank

student_answer_history (or inside attempts)

Update student ai_profile fields in Module 1

Advanced (after MVP works)
This is where your “Company Research Agent + Orchestrator Agent” comes in.

Company Interview Knowledge DB:

Build a reusable company_interview_knowledge collection (company, role, rounds, topics, behavioral themes).

Orchestrator:

Rule-guided difficulty adjustment (increase/decrease based on last answer + time + correctness).

Adaptive follow-ups:

Ask deeper questions on weak points, or probe inconsistencies across answers.

The exact components to build (engineering view)
1) Collections (MongoDB)
company_interview_knowledge

{company, role, rounds, patterns, sources[], updated_at}

question_bank

{type: "DSA|RESUME_TECH|BEHAVIORAL", tags[], difficulty, prompt, ideal_answer_outline, tests(need to implement this also)}

interview_sessions

{student_id, company, role, jd_id(need to implement this also), status, current_round, created_at}

interview_attempts

{session_id, round, question_id, student_answer, score, feedback, time_taken, created_at}

2) Core APIs (FastAPI)
POST /interview/session/start (create session)

GET /interview/session/{id}/next-question (orchestrator decides)

POST /interview/session/{id}/submit-answer

GET /interview/session/{id}/report (scores + improvement plan)

POST /interview/knowledge/company/sync (admin-only: build/update company knowledge)

3) UI (React)
Interview “lobby” (choose company/role, upload resume/JD)

Round screens:

Coding editor + run/submit

Chat-style Q&A (technical + behavioral)

Report screen (scores + next steps + reusable attempt history)

Important: keep it FREE + safe
Start with student-provided JD + resume (no scraping needed in MVP).

Add company research later using curated sources only, and store “sources” in DB so you can show “where the pattern came from” (reduces hallucinations).

Use open-source + free-tier LLM calls only (Gemini free-tier or open-source local later).

