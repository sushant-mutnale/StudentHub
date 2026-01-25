WEEK 7-8: Integration + Testing
Step 1: Connect Resume → JD → Company Knowledge → Interview Start
What you're building:

Full flow from student input to first interview question

What to do:

Trace the flow:

text
Student uploads resume → API parses resume → stored in DB
Student pastes JD → API parses JD → stored in session
Student selects company/role → API fetches company knowledge
API calls Orchestrator → Orchestrator decides first question
API returns first question to frontend
Test each step manually:

Upload resume → check MongoDB for parsed data

Parse JD → check response contains skills, role, company

Fetch company knowledge → check response has rounds, themes

Get first question → check question matches company/difficulty

Why this matters:
You verify the pipeline works end-to-end.

Step 2: Test Interview Loop
What you're building:

Full interview session: answer question → get evaluation → get next question

What to do:

Manually test:

Start interview for "Amazon SDE" role

Receive first DSA question

Submit your answer

Check if evaluation is correct (check correctness score)

Check if next question is appropriate difficulty

Complete 2-3 questions

Check if system moves to next round

Debug issues:

If evaluation wrong: check evaluation logic

If question irrelevant: check company knowledge

If difficulty not adapting: check orchestrator logic

Why this matters:
Interview is the core feature. Must work flawlessly.

Step 3: Test Report Generation
What you're building:

Report shows scores by round, strengths, weaknesses, recommendations

What to do:

Complete one full mock interview

Call report endpoint

Check if report shows:

✅ Overall score (average of all rounds)

✅ Round-by-round breakdown

✅ Top 3 strengths

✅ Top 3 weaknesses

✅ Learning recommendations

Why this matters:
Report is how students understand performance. Must be accurate + actionable.

Step 4: Integration with Module 1 (Update AI Profile)
What you're building:

After interview, student's AI profile updates

What to do:

After interview completes:

Get interview score from report

Update student's ai_profile.interview_score in MongoDB

Update ai_profile.overall_score (weighted average of all scores)

Log activity: {type: "INTERVIEW_COMPLETED", company: "Amazon", score: 85}

Verify in MongoDB:

Find student document

Check if interview_score updated

Check if activity logged

Why this matters:
Module 3 feeds back into Module 1. AI profile becomes more accurate over time.

Step 5: Integration with Module 2 (Better Matching)
What you're building:

Updated student profile → recruiters see better matches

What to do:

When recruiter views "matching students" for a job:

System now uses updated ai_profile.interview_score

Student who practiced interviews scores higher

Matching becomes more meaningful

Test:

Have recruiter view matching students before + after interview

Verify ranking improved

Why this matters:
Interview practice → better profile → better matching → more placements.

DELIVERABLES BY WEEK
Week	What's Done	Student Can Do
Week 2	Resume parsing	Upload resume, see parsed data
Week 3	JD parsing	Paste JD, see parsed job details
Week 4	Company knowledge	See interview patterns for companies
Week 5	Session management	Start interview, navigate rounds
Week 6	Q&A evaluation	Complete questions, see scores + feedback
Week 7	Full flow	Complete mock interview end-to-end
Week 8	Integration	See updated profile, better job matching