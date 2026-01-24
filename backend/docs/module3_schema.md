# Module 3 Database Schema Documentation

This document describes the MongoDB collections used by Module 3: Learning & Interview Prep.

## Collections Overview

| Collection | Purpose |
|------------|---------|
| `learning_paths` | Stores personalized learning roadmaps per student per skill |
| `learning_progress` | Tracks completion of individual resources |
| `interview_sessions` | Tracks mock interview attempts |
| `interview_questions` | Question bank (DSA, Technical, Behavioral) |
| `interview_attempts` | Student answers + scores per question |
| `company_interview_knowledge` | Company-specific interview patterns |
| `interview_reports` | Final interview reports with improvement plans |

---

## Schema Definitions

### learning_paths
```json
{
  "_id": "ObjectId",
  "student_id": "ObjectId",
  "skill": "aws",
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
          "resource_id": "uuid",
          "type": "video",
          "title": "AWS in 10 Minutes",
          "url": "https://youtube.com/...",
          "duration_minutes": 10,
          "source": "YouTube",
          "completed": false,
          "completed_at": null
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
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### interview_sessions
```json
{
  "_id": "ObjectId",
  "student_id": "ObjectId",
  "company": "Google",
  "role": "SDE Intern",
  "resume_text": "...",
  "jd_text": "...",
  "status": "in_progress|completed|abandoned",
  "current_round": 1,
  "rounds": ["dsa", "technical_qa", "behavioral"],
  "created_at": "datetime",
  "completed_at": null
}
```

### interview_attempts
```json
{
  "_id": "ObjectId",
  "session_id": "ObjectId",
  "round": "dsa",
  "question_id": "ObjectId",
  "student_answer": "...",
  "score": 85,
  "feedback": "Good approach, but consider edge cases...",
  "time_taken_seconds": 1200,
  "created_at": "datetime"
}
```
