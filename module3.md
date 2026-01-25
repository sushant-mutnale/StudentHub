WEEK 5: Interview Session Management
Step 1: Design Interview Session Flow
What you're building:

A session that tracks: which round, which question, student's answers, scores

Flow diagram (text version):

text
1. Student fills: Company, Role, Resume, JD
2. System creates SESSION
3. System gets first QUESTION
4. Student answers
5. System evaluates answer
6. System decides: next question OR next round OR complete
7. Go to step 3 until done
8. Generate REPORT
What to do:

Draw this flow on paper/whiteboard

Identify decision points:

How many questions per round?

When to move to next round?

When to end interview?

Write down the logic (in English, not code):

"If student completes 2 questions in a round, move to next round"

"If student completes all rounds, generate report"

Why this matters:
Clear flow prevents bugs. You know exactly what should happen at each step.

Step 2: Create Interview Session Data Model
What you're building:

MongoDB collection: interview_sessions

Stores all data for one interview from start to end

What to do:

Design the document structure:

session_id

student_id

company_name

role

job_description (full text)

resume_parsed (extracted skills, experience)

status (not_started, in_progress, completed)

current_round (which round are we on?)

rounds array (each round has: questions answered, score)

overall_score

created_at, updated_at

Example:

text
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "company": "Amazon",
  "role": "SDE",
  "status": "in_progress",
  "current_round": 0,
  "rounds": [
    {
      "round_num": 0,
      "type": "dsa",
      "name": "Coding Round",
      "questions_answered": 1,
      "score": 75
    }
  ],
  "overall_score": 0,
  "created_at": "2026-01-24T..."
}
Why this matters:
This is your source of truth for what's happening in the interview.

Step 3: Create Interview Orchestrator Logic
What you're building:

The "brain" that decides what happens next

What to do:

Write down the logic for each decision:

Decision 1: Which question to ask?

Look at current round type (DSA, behavioral, design)

Look at company knowledge base

Look at student resume (for personalization)

Pick a question that fits

Decision 2: Adapt difficulty?

If previous answer scored >80% → increase difficulty

If <50% → decrease difficulty

Else → keep same

Decision 3: Move to next round?

Count questions answered in current round

If ≥ 2 → move to next round

Else → ask another question in same round

Decision 4: End interview?

If current_round ≥ total_rounds → end

Generate report

Write this as pseudocode (English, not Python):

text
FUNCTION get_next_question(session):
    IF current_round >= total_rounds:
        RETURN "interview_completed"
    
    current_round_data = session.rounds[session.current_round]
    
    previous_score = get_previous_score(session)
    difficulty = adapt_difficulty(previous_score)
    
    question = find_question(
        type: current_round_data.type,
        company: session.company,
        difficulty: difficulty
    )
    
    RETURN question

FUNCTION decide_next_action(session, evaluation_score):
    questions_in_round = count_questions_in_current_round(session)
    
    IF questions_in_round >= 2:
        RETURN "move_to_next_round"
    ELSE:
        RETURN "continue_in_same_round"
Why this matters:
Clear logic = clear API design = correct implementation.

Step 4: Create Interview Session APIs
What you're building:

API endpoints to manage interview lifecycle

What to do:

Design these endpoints:

POST /api/interview/start

Input: company, role, resume_id, jd_text

Output: session_id, first_question

Action: Create session, get first question

GET /api/interview/next-question?session_id={id}

Input: session_id

Output: next_question details

Action: Get next question based on orchestrator logic

POST /api/interview/submit-answer

Input: session_id, question_id, student_answer, time_taken

Output: evaluation, next_action

Action: Evaluate answer, decide next step

GET /api/interview/report/{session_id}

Input: session_id

Output: full report with scores, strengths, weaknesses

Action: Generate report after interview complete

For each endpoint, write the logic in English:

What inputs do you need?

What do you check/validate?

What database operations?

What output?

Why this matters:
Clear API contracts make implementation straightforward.