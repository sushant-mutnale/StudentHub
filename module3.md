WEEK 3: Job Description Parsing
Step 1: Understand Job Description Structure
What you need to know:

Job descriptions have sections: Title, Company, Requirements, Responsibilities, Qualifications

Required skills are listed under "Requirements", "Must have", "Essential"

Nice-to-have skills under "Preferred", "Nice to have", "Bonus"

Experience level mentioned (entry-level, junior, mid, senior)

Salary range sometimes included

What to do:

Collect 5 sample job descriptions (from LinkedIn, job boards)

For each one, manually identify:

Where is the job title?

Where are required skills?

Where are nice-to-have skills?

What's the experience level?

Where are responsibilities listed?

Look for patterns (keywords, formatting)

Why this matters:
JD parsing is different from resume parsing. You need the patterns.

Step 2: Create JD Parser Service
What you're building:

A service that takes job description text (plain text input)

Returns structured JSON with: job_title, required_skills, nice_to_have_skills, experience_level, company, salary_range, responsibilities, qualifications

What to do:

Create file: backend/services/jd_parser.py

Create class: JobDescriptionParser with methods:

parse_jd() - Main method

extract_required_skills() - Parse required skills section

extract_nice_to_have_skills() - Parse preferred skills

extract_experience_level() - Determine seniority

extract_job_title() - Find title

extract_company() - Find company name

extract_responsibilities() - Parse duties section

extract_qualifications() - Parse qualifications section

Parsing strategy:

Split JD text into sections (look for headers: "Requirements", "Responsibilities", etc.)

For each section, extract relevant information using:

Pattern matching (regex for dates, emails)

Keyword matching (if text contains "Python", extract it as skill)

Text normalization (lowercase, trim spaces)

Why this matters:
JD parsing is how you understand what a job needs. This becomes input to matching + question generation.

Step 3: Create Skill Normalization
What you're building:

A dictionary/mapping that normalizes skill names

Example: "ReactJS" → "React", "node.js" → "nodejs"

What to do:

Create file: backend/services/skill_normalizer.py

Build a mapping dictionary of common variations:

text
{
  "reactjs": "react",
  "react.js": "react",
  "node": "nodejs",
  "node.js": "nodejs",
  "python3": "python",
  "py": "python",
  "sql": "databases",
  "mongo": "mongodb",
  "etc...
}
Create a function: normalize_skill(skill_name) that:

Converts to lowercase

Removes spaces, dots, hyphens

Looks up in the mapping dictionary

Returns normalized name

Why this matters:
When matching student skills to job requirements, "React" ≠ "ReactJS" unless you normalize them.

Step 4: Create JD Parsing API Endpoint
What you're building:

An endpoint where students paste job description text

Backend parses it, returns structured JSON

What to do:

In backend/routes/interview.py, add endpoint: POST /api/interview/parse-job-description

This endpoint should:

Receive JD text as string in request body

Call JobDescriptionParser.parse_jd(jd_text)

Return parsed data as JSON

Request format:

json
{
  "jd_text": "Job Description text here..."
}
Response format:

json
{
  "job_title": "Backend Engineer",
  "company": "Amazon",
  "required_skills": ["Python", "AWS", "System Design"],
  "nice_to_have_skills": ["Kubernetes", "Go"],
  "experience_level": "mid",
  "responsibilities": [...],
  "qualifications": [...],
  "salary_range": {"min": 100000, "max": 150000}
}
Why this matters:
Now students can paste JD → backend parses → structured data for matching + questions.

Step 5: Test JD Parsing
What to do:

Collect one job description (copy from LinkedIn)

Use API to parse it

Check if it correctly extracted:

✅ Job title?

✅ Required skills?

✅ Company name?

✅ Experience level?

Debug any failures

Why this matters:
Same reason as resume testing—catch errors early.