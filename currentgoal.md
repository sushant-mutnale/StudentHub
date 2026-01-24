WEEK 1: SETUP & LEARNING PATHS FOUNDATION
DAY 1-2: Project Setup & Dependencies
Step 1: Set Up Module 3 Project Structure
What you're building:

Organized folder structure for Module 3 inside your existing StudentHub backend

What to do:

Inside backend/, create this structure:

text
backend/
├── services/
│   ├── resume_parser.py (you'll create Week 2)
│   ├── jd_parser.py (you'll create Week 3)
│   ├── skill_normalizer.py (Week 2-3)
│   ├── gap_analyzer.py (Week 1 - TODAY)
│   ├── learning_path_builder.py (Week 1 - TODAY)
│   ├── company_research.py (Week 4)
│   ├── interview_orchestrator.py (Week 5)
│   ├── question_generator.py (Week 6)
│   └── answer_evaluator.py (Week 6)
├── routes/
│   ├── interview.py (new routes for Module 3)
│   └── learning.py (new routes for learning paths)
├── models/ (if you use Pydantic models)
│   └── learning.py
└── utils/
    └── resource_scraper.py (fetch free resources)
This keeps everything organized and separates concerns

Why this matters:
Clean structure = easier debugging + easier team collaboration later.

Step 2: Install Required Python Libraries
What you're building:

Development environment ready for all Module 3 features

What to do:

Create a new file: backend/requirements_module3.txt

Add these libraries (you'll use them across all weeks):

text
# Core (already have)
fastapi
uvicorn
pydantic
pymongo

# PDF Parsing (Week 2)
pdfplumber
PyPDF2
pymupdf

# NLP & Text Processing (Week 2-3)
spacy
nltk
python-docx

# Resume Parsing (Week 2)
pyresparser

# AI/LLM (Week 6-7)
google-generativeai

# Code Execution (Week 6)
# (use subprocess - built-in, no install needed)

# Web Scraping for Resources (Week 1)
requests
beautifulsoup4

# Testing
pytest
Install all at once:

bash
pip install -r backend/requirements_module3.txt
Download spaCy English model:

bash
python -m spacy download en_core_web_sm
Download NLTK data:

python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
Why this matters:
Installing everything upfront prevents "dependency hell" later. You can focus on building, not debugging imports.

Step 3: Set Up MongoDB Collections for Module 3
What you're building:

Database schema for Learning Paths + Interviews

What to do:

Open MongoDB Compass (or CLI)

Inside your studenthub database, create these NEW collections:

learning_paths - stores learning roadmaps per student

learning_progress - tracks what student completed

interview_sessions - tracks interview attempts

interview_questions - question bank

interview_attempts - student answers + scores

company_interview_knowledge - company interview patterns

interview_reports - final reports

Don't create documents yet — just create the empty collections

Document the purpose of each collection in a file: backend/docs/module3_schema.md

Why this matters:
Pre-planning your database prevents schema changes later (which break existing code).

DAY 3-4: Skill Gap Analysis Engine
Step 1: Understand What Skill Gap Analysis Means
What you're building:

A system that compares "what student has" vs "what job needs" and outputs "what's missing"

What to do:

Write down the formula (in plain English):

text
Student Skills = ["Python", "React", "MongoDB"]
Job Required Skills = ["Python", "AWS", "Docker", "System Design"]
Job Nice-to-Have = ["Kubernetes", "React"]

Gap = Required - Student
     = ["AWS", "Docker", "System Design"]

Priority:
- AWS: HIGH (required and missing)
- Docker: HIGH (required and missing)
- System Design: HIGH (required and missing)
- Kubernetes: MEDIUM (nice-to-have and missing)
Identify scoring logic:

text
Gap Score = (Number of missing required skills / Total required skills) * 100

Example:
Missing 3 out of 4 required → Gap Score = 75% (BAD - big gap)
Missing 1 out of 4 required → Gap Score = 25% (GOOD - small gap)
Draw a simple diagram on paper:

text
[Student Skills] → Compare → [Job Required Skills] → Output → [Gap List + Priority]
Why this matters:
Understanding the logic first prevents coding bugs. If you can't explain it in English, you can't code it.

Step 2: Design Gap Analysis Data Structure
What you're building:

The output format of gap analysis

What to do:

Design what the output should look like (JSON structure):

json
{
  "student_id": "ObjectId",
  "job_id": "ObjectId (optional)",
  "analyzed_at": "2026-01-24T...",
  "student_skills": ["Python", "React", "MongoDB"],
  "job_required_skills": ["Python", "AWS", "Docker", "System Design"],
  "job_nice_to_have": ["Kubernetes", "React"],
  "gaps": [
    {
      "skill": "AWS",
      "priority": "HIGH",
      "reason": "Required but missing",
      "current_level": 0,
      "target_level": 80
    },
    {
      "skill": "Docker",
      "priority": "HIGH",
      "reason": "Required but missing",
      "current_level": 0,
      "target_level": 80
    }
  ],
  "match_percentage": 25,
  "gap_score": 75,
  "recommendations": "Focus on AWS and Docker first"
}
This becomes your "contract" — what the Gap Analyzer must return

Why this matters:
Clear data structure = clear API design = clear frontend implementation.

Step 3: Create Skill Gap Analyzer Service
What you're building:

A service that takes student skills + job skills, outputs gap analysis

What to do:

Create file: backend/services/gap_analyzer.py

Inside, create class: SkillGapAnalyzer with these methods:

Method 1: analyze_gap(student_skills, job_required, job_nice_to_have)

Input: 3 lists of skills

Output: Gap analysis object (like JSON above)

Logic:

Find missing required skills (set difference)

Find missing nice-to-have skills

Assign priority (required = HIGH, nice-to-have = MEDIUM)

Calculate match percentage

Generate recommendations

Method 2: normalize_skills(skills_list)

Input: List of skills (might have variations like "ReactJS", "React.js")

Output: Normalized list (all become "react")

Logic:

Lowercase all

Remove spaces, dots, hyphens

Apply synonym mapping (create a simple dict for now)

Method 3: calculate_priority(skill, is_required, student_has_similar)

Input: skill name, is it required?, does student have similar skill?

Output: Priority level (HIGH, MEDIUM, LOW)

Logic:

If required and completely missing → HIGH

If required but student has similar (e.g., "React Native" when need "React") → MEDIUM

If nice-to-have and missing → MEDIUM

If student already has it → LOW (no gap)

Write the logic in pseudocode first (not Python yet):

text
FUNCTION analyze_gap(student_skills, job_required, job_nice_to_have):
    student_normalized = normalize_skills(student_skills)
    required_normalized = normalize_skills(job_required)
    nice_normalized = normalize_skills(job_nice_to_have)

    missing_required = required_normalized - student_normalized
    missing_nice = nice_normalized - student_normalized

    gaps = []
    FOR each skill in missing_required:
        gaps.append({
            skill: skill,
            priority: "HIGH",
            reason: "Required but missing"
        })

    FOR each skill in missing_nice:
        gaps.append({
            skill: skill,
            priority: "MEDIUM",
            reason: "Nice-to-have but missing"
        })

    match_percentage = (student has / total required) * 100
    gap_score = 100 - match_percentage

    RETURN gap_analysis_object
Why this matters:
Pseudocode lets you think through logic without syntax errors. Once it's clear, Python becomes easy.

Step 4: Create Gap Analysis API Endpoint
What you're building:

An endpoint where frontend sends student skills + job skills, backend returns gap analysis

What to do:

Create file: backend/routes/learning.py

Add endpoint: POST /api/learning/analyze-gap

Request format:

json
{
  "student_id": "ObjectId",
  "student_skills": ["Python", "React"],
  "job_id": "ObjectId (optional)",
  "job_required_skills": ["Python", "AWS", "Docker"],
  "job_nice_to_have_skills": ["Kubernetes"]
}
Response format:

json
{
  "status": "success",
  "gap_analysis": {
    "gaps": [...],
    "match_percentage": 33,
    "gap_score": 67,
    "recommendations": "Focus on AWS and Docker"
  }
}
Endpoint logic (in English):

Receive student skills + job skills

Call SkillGapAnalyzer.analyze_gap()

Store gap analysis in MongoDB (learning_paths collection)

Return gap analysis to frontend

Why this matters:
API is how frontend talks to backend. Clear contract = smooth integration.

Step 5: Test Gap Analysis Manually
What to do:

Use Postman or curl to test:

text
POST /api/learning/analyze-gap
Body:
{
  "student_skills": ["Python", "React"],
  "job_required_skills": ["Python", "AWS", "Docker", "System Design"]
}
Check response:

✅ Does it show missing skills (AWS, Docker, System Design)?

✅ Are priorities correct (all HIGH because required)?

✅ Is match percentage correct (25% = 1 out of 4)?

Test edge cases:

What if student has ALL skills? (gap = 0%)

What if student has NO skills? (gap = 100%)

What if skills have typos? (normalization should fix)

Why this matters:
Manual testing catches bugs early before frontend integration.

DAY 5-7: Learning Path Builder
Step 1: Understand What a Learning Path Is
What you're building:

A roadmap that tells student: "To learn AWS, do these steps in this order"

What to do:

Write down what a learning path should contain:

text
Learning Path for "AWS":

Stage 1: Foundation (2 weeks)
- Topic: What is cloud computing?
- Resources:
  - Video: "AWS Basics" (YouTube, 1 hour)
  - Article: "Intro to AWS" (FreeCodeCamp)
- Assessment: Quiz (10 questions)

Stage 2: Core Services (3 weeks)
- Topic: EC2, S3, RDS
- Resources:
  - Course: "AWS Fundamentals" (Coursera free audit)
  - Practice: Deploy a simple app on EC2
- Assessment: Hands-on project

Stage 3: Advanced (2 weeks)
- Topic: Auto-scaling, Load Balancing
- Resources: ...
- Assessment: ...
Break it into components:

Stages: Beginner → Intermediate → Advanced

Topics: What to learn in each stage

Resources: Where to learn (videos, articles, courses)

Assessments: How to verify learning (quiz, project)

Duration: How long each stage takes

Why this matters:
Clear structure = students know exactly what to do next. No overwhelm.

Step 2: Design Learning Path Data Structure
What you're building:

MongoDB document structure for learning paths

What to do:

Design the schema:

json
{
  "_id": "ObjectId",
  "student_id": "ObjectId",
  "skill": "AWS",
  "current_level": 0,
  "target_level": 80,
  "gap_priority": "HIGH",
  "stages": [
    {
      "stage_number": 1,
      "stage_name": "Foundation",
      "duration_weeks": 2,
      "topics": ["What is AWS?", "Core services overview"],
      "resources": [
        {
          "type": "video",
          "title": "AWS in 10 Minutes",
          "url": "https://youtube.com/...",
          "duration_minutes": 10,
          "source": "YouTube"
        },
        {
          "type": "article",
          "title": "AWS Basics",
          "url": "https://freecodecamp.org/...",
          "reading_time_minutes": 15,
          "source": "FreeCodeCamp"
        }
      ],
      "assessment": {
        "type": "quiz",
        "questions_count": 10,
        "passing_score": 70
      },
      "status": "not_started",
      "completed_at": null
    }
  ],
  "progress": {
    "current_stage": 0,
    "completion_percentage": 0,
    "time_spent_minutes": 0,
    "estimated_completion_date": "2026-03-01"
  },
  "created_at": "2026-01-24T...",
  "updated_at": "2026-01-24T..."
}
This becomes the template for ALL learning paths

Why this matters:
Structured data = you can show progress bars, calculate completion %, recommend next steps.

Step 3: Find Free Learning Resources
What you're building:

A curated list of FREE resources for common tech skills

What to do:

For each skill, find 3-5 free resources:

Example for "AWS":

YouTube: "AWS Tutorial for Beginners" (FreeCodeCamp)

Course: AWS Cloud Practitioner (Coursera free audit)

Article: AWS Documentation (official)

Practice: AWS Free Tier hands-on labs

Example for "Docker":

YouTube: "Docker Crash Course" (TechWorld with Nana)

Article: "Docker for Beginners" (GeeksforGeeks)

Interactive: Docker Playground (free online sandbox)

Example for "System Design":

YouTube: "System Design Primer" (Gaurav Sen)

Article: "System Design Interview Guide" (GitHub repo)

Book: "Designing Data-Intensive Applications" (free PDF)

Create a mapping file: backend/data/learning_resources.json

json
{
  "aws": [
    {
      "type": "video",
      "title": "AWS in 10 Minutes",
      "url": "https://youtube.com/...",
      "duration_minutes": 10,
      "level": "beginner"
    }
  ],
  "docker": [...],
  "system_design": [...]
}
Start with 10-15 common skills (you can expand later)

Why this matters:
You can't build learning paths without resources. Curating them once saves time for every student.

Step 4: Create Learning Path Builder Service
What you're building:

A service that takes a skill gap, generates a learning path

What to do:

Create file: backend/services/learning_path_builder.py

Create class: LearningPathBuilder with methods:

Method 1: build_path(skill, current_level, target_level, priority)

Input: skill name, current proficiency (0-100), target proficiency (0-100), priority

Output: Learning path object (like JSON structure above)

Logic:

Determine number of stages based on gap size

For each stage, fetch resources from learning_resources.json

Assign topics per stage (foundation → intermediate → advanced)

Calculate estimated duration

Return learning path

Method 2: fetch_resources(skill, level)

Input: skill name, difficulty level (beginner/intermediate/advanced)

Output: List of resources

Logic:

Load learning_resources.json

Filter by skill and level

Return top 3-5 resources

Method 3: estimate_duration(current_level, target_level)

Input: current and target proficiency

Output: estimated weeks

Logic:

Gap = target - current

If gap < 30 → 2 weeks

If gap 30-60 → 4 weeks

If gap > 60 → 6-8 weeks

Write pseudocode first:

text
FUNCTION build_path(skill, current_level, target_level, priority):
    gap = target_level - current_level
    
    IF gap < 30:
        stages = 1 (foundation only)
    ELSE IF gap < 60:
        stages = 2 (foundation + intermediate)
    ELSE:
        stages = 3 (foundation + intermediate + advanced)

    learning_path = {
        skill: skill,
        stages: []
    }

    FOR i in 1 to stages:
        stage = {
            stage_number: i,
            topics: get_topics_for_stage(i),
            resources: fetch_resources(skill, stage_level),
            duration_weeks: calculate_stage_duration(gap)
        }
        learning_path.stages.append(stage)

    RETURN learning_path
Why this matters:
Automated path generation = scalable. One service creates paths for thousands of students.

Step 5: Create Learning Path API Endpoint
What you're building:

An endpoint that takes gap analysis, generates learning paths

What to do:

In backend/routes/learning.py, add endpoint: POST /api/learning/generate-path

Request format:

json
{
  "student_id": "ObjectId",
  "gaps": [
    {
      "skill": "AWS",
      "priority": "HIGH",
      "current_level": 0,
      "target_level": 80
    },
    {
      "skill": "Docker",
      "priority": "HIGH",
      "current_level": 0,
      "target_level": 80
    }
  ]
}
Response format:

json
{
  "status": "success",
  "learning_paths": [
    {
      "skill": "AWS",
      "stages": [...],
      "estimated_completion_weeks": 6
    },
    {
      "skill": "Docker",
      "stages": [...],
      "estimated_completion_weeks": 4
    }
  ]
}
Endpoint logic:

Receive gap list

For each gap, call LearningPathBuilder.build_path()

Store each learning path in MongoDB (learning_paths collection)

Return all learning paths to frontend

Why this matters:
This is how students get their personalized roadmap after gap analysis.

Step 6: Create Progress Tracking
What you're building:

A way for students to mark resources as "completed"

What to do:

Add endpoint: POST /api/learning/mark-progress

Request format:

json
{
  "learning_path_id": "ObjectId",
  "stage_number": 1,
  "resource_index": 0,
  "action": "completed"
}
Logic:

Find learning path in MongoDB

Mark resource as completed

Update progress percentage

If all resources in a stage completed → mark stage as complete

If all stages complete → update student profile (skill level increased)

Add endpoint: GET /api/learning/my-paths?student_id={id}

Returns all active learning paths for student

Shows progress for each

Why this matters:
Progress tracking = motivation. Students see their growth visually.

Step 7: Test Learning Path Generation
What to do:

Test end-to-end flow:

text
Step 1: Analyze gap
POST /api/learning/analyze-gap
→ Get gap analysis with ["AWS", "Docker"]

Step 2: Generate learning paths
POST /api/learning/generate-path
→ Get learning path for AWS (3 stages) + Docker (2 stages)

Step 3: View paths
GET /api/learning/my-paths?student_id=...
→ See both paths with progress = 0%

Step 4: Mark progress
POST /api/learning/mark-progress
→ Mark first video as complete
→ Progress updates to 10%
Verify in MongoDB:

Check learning_paths collection has documents

Check progress fields update correctly

Why this matters:
Full flow testing ensures all pieces connect properly.

WEEK 1 DELIVERABLES SUMMARY
By end of Week 1, you have:

Component	What's Built	Student Can Do
Gap Analyzer	Service + API	See what skills they're missing for a job
Learning Path Builder	Service + API	Get personalized learning roadmap
Resource Library	Curated JSON file	Access free videos, articles, courses
Progress Tracker	API endpoints	Mark resources complete, see progress %
Database	Collections setup	All data stored and queryable
WEEK 1 vs WEEK 2-8 CONNECTION