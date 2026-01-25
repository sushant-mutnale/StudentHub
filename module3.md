WEEK 6: Question Generation & Answer Evaluation
Step 1: Design Question Types
What you're building:

Different question types: DSA (coding), Behavioral (STAR format), Design (architecture), Technical (resume-based)

What to do:

For each question type, define:

DSA Question:

Title: "Two Sum"

Description: Problem statement

Constraints: Input/output limits

Examples: Input/output samples

Test cases: Hidden tests for auto-evaluation

Ideal answer: Solution approach + time complexity

Behavioral Question:

Theme: What company value? (leadership, ownership, etc.)

Question: "Tell me about a time when..."

Expected format: STAR (Situation, Task, Action, Result)

Evaluation criteria: Does it follow STAR? Is it detailed?

Design Question:

Topic: "Design a URL shortener"

Requirements: Scalability, components needed

Expected approach: Explain architecture, discuss tradeoffs

Technical Question:

Based on student's resume projects

Example: "I see you built a recommendation system. How did you handle cold start problem?"

Design MongoDB collection: interview_questions

For each question type, what fields do you need to store?

Why this matters:
You understand what information each question needs. Makes generation easier.

Step 2: Create Question Generation Strategy
What you're building:

Logic for where to find/create questions

What to do:

For DSA questions, think about workflow:

First, check question bank (MongoDB) for questions matching: company + difficulty + topic

If found, use it

If not found, either:

a) Return a generic question, or

b) Generate using LLM (Gemini API free-tier)

For Behavioral questions:

Get company behavioral themes from knowledge base

Generate question using LLM prompt

Example prompt: "Generate a leadership principle question for Amazon"

For Design questions:

Use pre-defined list of common designs

Rotate them (so not same question every time)

For Technical questions:

Parse student's resume

Pick one project

Generate follow-up questions about it

Write this as a decision tree:

text
IF question_type == "DSA":
    IF question exists in DB → use it
    ELSE → generate with LLM
ELSE IF question_type == "behavioral":
    GET company themes → generate with LLM
ELSE IF question_type == "design":
    PICK from pre-defined list
ELSE IF question_type == "technical":
    GET student's projects → generate with LLM
Why this matters:
You know where questions come from—no magic, just clear workflow.

Step 3: Design Answer Evaluation Strategy
What you're building:

How to evaluate each question type

What to do:

For DSA answers:

Run code against test cases → correctness score

Analyze code for quality (naming, comments, structure) → code quality score

Estimate time/space complexity → efficiency score

Calculate final score as weighted average

For Behavioral answers:

Check if answer has Situation, Task, Action, Result → STAR score

Count words/details → depth score

Check for company-specific keywords → alignment score

For Design answers:

Check if mentions key components (frontend, backend, database, cache) → architecture score

Check if discusses scalability → scalability score

Check if discusses tradeoffs → thinking score

For Technical answers:

Check if explains concepts clearly → clarity score

Check if uses technical terminology correctly → accuracy score

Check if goes deep (multiple levels) → depth score

Scoring formula (example):

text
For DSA:
  overall_score = (correctness * 0.4) + (code_quality * 0.3) + (efficiency * 0.2) + (speed * 0.1)

For Behavioral:
  overall_score = (STAR_score * 0.6) + (depth_score * 0.4)
Why this matters:
Clear evaluation criteria = fair scoring = student trust.

Step 4: Create Evaluation Feedback
What you're building:

Constructive feedback for each answer (not just a score)

What to do:

For each evaluation, generate feedback like:

DSA: "Your solution is correct and efficient! Consider adding edge case handling for empty arrays."

Behavioral: "Great STAR format! Next time, add more specific metrics/outcomes."

Design: "Good architecture thinking. How would you handle 1 million concurrent users?"

Feedback should be:

Specific (mention what they did right + wrong)

Actionable (suggest improvement)

Encouraging (reinforce positives)

Use LLM (Gemini) to generate feedback:

Prompt: "Generate constructive feedback for this code: [code]"

Why this matters:
Feedback helps students learn. Scores alone are meaningless.