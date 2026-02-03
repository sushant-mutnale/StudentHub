Module 1: User & Profile Management
Done: auth, profiles, AI career profile, structured skills, profile update loop. (This matches your module definition.)

Module 2: Evaluation & Matching
Mostly done: matching algorithm, job requirements analysis, ranked candidates, score integration.

Module 3: Learning & Feedback
Done: resume/JD parsing, gap analysis, learning paths, mock interviews, evaluator, multi-agent system, code sandbox, research tool.

Module 4: Recommendation & Notification
Not done / only partial: you don’t yet have a full external opportunities recommendation engine (jobs/competitions/content), nor a dedicated notification rules engine that triggers alerts based on AI profile changes. This module also needs safe sourcing because many platforms don’t provide official free APIs; you’ll rely on approved sources or scrapers/aggregators (e.g., Apify actors for Internshala scraping exist).
​

Module 5: Communication & Tracking
Partially done: you have messaging + interviews scheduling + offers.
Still missing (as per your definition): full recruitment stage tracking, centralized “status timeline”, and structured feedback/outcome tracking across the entire journey (not only interview events).

Remaining two modules: proper plan
Module 4: Recommendation & Notification (External opportunities + alerts)
Goal: “Based on AI profile + progress, recommend opportunities and notify users.”

Phase A (Week 1): Data sources + ingestion
What to do:

Decide 3 external “buckets”:

Jobs/Internships, 2) Competitions/Hackathons, 3) Trending content/insights.

Start with sources you can actually integrate:

Internships/jobs: use aggregators/scrapers (example: Internshala scraping via Apify actor exists; you can integrate via HTTP API).
​

Hackathons: Devpost is a hub for hackathons (API is not official, so treat as scrape/links-first).
​

Create a nightly ingestion job:

Pull new items → normalize fields → store in MongoDB collections:

opportunities_jobs, opportunities_hackathons, opportunities_content.

Phase B (Week 2): Recommendation engine
What to do:

Build ranking logic (no code here, just workflow):

Inputs: student skills, ai_profile scores, learning gaps, location, graduation year.

Score each opportunity:

Skill overlap score

Freshness score (newer = higher)

Difficulty fit (based on ai_profile)

Interest signals (saved/ignored history)

Add endpoints:

GET /recommendations/jobs

GET /recommendations/hackathons

GET /recommendations/content

Add “save / ignore / apply-click” tracking (this becomes your feedback loop for better ranking).

Phase C (Week 3): Notification rules engine
What to do:

Create notification triggers like:

“New job matches your skills above 75%”

“Hackathon closing soon + matches your stack”

“Skill gap remains high for AWS → notify learning reminder”

Create delivery channels:

In-app notifications first (simple + reliable)

Email later (optional)

Deliverable: students get a personalized feed + notifications, recruiters get alerts for top candidates.

Module 5: Communication & Tracking (Recruitment workflow timeline)
Goal: “Real hiring workflow tracking inside the platform, not just messaging.”

Phase A (Week 1): Recruitment stage tracker
What to do:

Define canonical stages (example):

Applied → Shortlisted → Interview Scheduled → Interview Completed → Offer Extended → Offer Accepted/Rejected.

Create a single “application tracking record” per (student, job):

Stores current stage + stage history (timestamps + actor).

Add endpoints:

POST /applications/{id}/move-stage

GET /applications/my (student)

GET /jobs/{id}/pipeline (recruiter)

Phase B (Week 2): Feedback + outcome capture (structured)
What to do:

Standardize feedback forms:

Interview feedback already exists; expand to include:

shortlisting feedback

rejection reason

offer notes

Store structured evaluations so Module 2 scoring can use them.

Phase C (Week 3): Tight integration with module loops
What to do:

Every stage change updates:

student ai_profile.activity_score and interview_score

recruiter analytics counters

Add “communication context linking”:

messages tied to application + interview session.

Deliverable: a clean recruitment pipeline view for recruiter + a transparent timeline for students.

“Similar services” reference (what to copy, but upgraded)
For Module 4:

Opportunity aggregators (jobs + internships) → you can implement via structured ingestion and scoring; Apify provides ready scraping APIs for sites like Internshala, which reduces engineering work.
​

Hackathon discovery hubs like Devpost → use listing/links + metadata; later automate.
​

For Module 5:

ATS-style pipeline timeline (stage-based tracking + history) combined with your unique AI evaluation loop (this is your “upgrade” over normal ATS).