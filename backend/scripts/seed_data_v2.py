"""
seed_data_v2.py — Comprehensive platform seeding script.

Creates:
  1. 3 Mock recruiters (Google India, Amazon, Infosys) with pipeline templates
  2. 5 jobs per recruiter (15 total)
  3. Updates student sushantmutnale512@gmail.com with matching skills
  4. Student applications to 1 job per recruiter (3 applications total)
  5. Message threads: student <-> each recruiter (3 threads, multi-message)
  6. Scheduled interviews: each recruiter proposes + auto-accepted (3 interviews)
  7. Notifications for each interaction

Run:
    cd d:\\python\\project\\StudentHub
    .\\venv\\Scripts\\Activate.ps1
    python -m backend.scripts.seed_data_v2
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from passlib.context import CryptContext

# ─────────────────────────── Config ────────────────────────────
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://Sush_512:Sushant%40512@studenthub.zlkxvkr.mongodb.net/?appName=Studenthub"
)
DB_NAME = os.getenv("MONGODB_DB", "student_hub")
STUDENT_EMAIL = "sushantmutnale512@gmail.com"

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto",
                           pbkdf2_sha256__default_rounds=390000)

def hp(pw): return pwd_context.hash(pw)

NOW = datetime.utcnow()

# ─────────────────────────── Recruiter definitions ─────────────
RECRUITERS = [
    {
        "username": "google_india_recruiter",
        "email": "careers@google-india.studenthub.demo",
        "password": "Demo@123",
        "full_name": "Priya Sharma",
        "role": "recruiter",
        "company_name": "Google India",
        "location": "Bangalore",
        "website": "https://careers.google.com",
        "company_description": "Google India hiring for SWE, ML, and Cloud roles.",
        "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=GI",
        "contact_number": "9876500001",
    },
    {
        "username": "amazon_dev_recruiter",
        "email": "careers@amazon.studenthub.demo",
        "password": "Demo@123",
        "full_name": "Rahul Mehta",
        "role": "recruiter",
        "company_name": "Amazon Development Center",
        "location": "Hyderabad",
        "website": "https://amazon.jobs",
        "company_description": "Amazon hiring engineers for AWS and e-commerce products.",
        "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=AM",
        "contact_number": "9876500002",
    },
    {
        "username": "infosys_bpm_recruiter",
        "email": "careers@infosys.studenthub.demo",
        "password": "Demo@123",
        "full_name": "Sneha Patil",
        "role": "recruiter",
        "company_name": "Infosys BPM",
        "location": "Pune",
        "website": "https://www.infosys.com/careers",
        "company_description": "Infosys BPM hiring freshers for technology and consulting roles.",
        "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=IB",
        "contact_number": "9876500003",
    },
]

# ─────────────────────────── Jobs per recruiter ─────────────────
JOBS_PER_RECRUITER = {
    "Google India": [
        {
            "title": "Software Development Engineer (Python/Backend)",
            "description": "Build scalable backend services powering Google's core products. Work on distributed systems, APIs, and cloud infrastructure.",
            "skills_required": ["Python", "Go", "Distributed Systems", "REST APIs", "Docker", "GCP"],
            "location": "Bangalore",
            "work_mode": "hybrid",
            "salary_range": "25 LPA - 45 LPA",
            "experience_required": "0-2 years",
            "url": "https://careers.google.com/jobs/",
        },
        {
            "title": "Machine Learning Engineer",
            "description": "Develop and deploy production ML models at scale. Work with TensorFlow, PyTorch and Google's ML infrastructure.",
            "skills_required": ["Python", "Machine Learning", "TensorFlow", "Data Science", "SQL"],
            "location": "Bangalore",
            "work_mode": "hybrid",
            "salary_range": "28 LPA - 50 LPA",
            "experience_required": "1-3 years",
            "url": "https://careers.google.com/jobs/",
        },
        {
            "title": "Frontend Engineer (React/TypeScript)",
            "description": "Build beautiful, performant UIs for Google Workspace products used by millions of users.",
            "skills_required": ["React", "TypeScript", "JavaScript", "CSS", "GraphQL"],
            "location": "Hyderabad",
            "work_mode": "remote",
            "salary_range": "20 LPA - 35 LPA",
            "experience_required": "0-2 years",
            "url": "https://careers.google.com/jobs/",
        },
        {
            "title": "Cloud Solutions Architect",
            "description": "Help customers design and migrate workloads to Google Cloud Platform. Deep expertise in GCP products.",
            "skills_required": ["GCP", "AWS", "Kubernetes", "Terraform", "Python", "Networking"],
            "location": "Mumbai",
            "work_mode": "onsite",
            "salary_range": "35 LPA - 60 LPA",
            "experience_required": "3-5 years",
            "url": "https://careers.google.com/jobs/",
        },
        {
            "title": "Data Analyst (Google Ads)",
            "description": "Analyze ad performance data to improve targeting algorithms. SQL-heavy role with exposure to BigQuery.",
            "skills_required": ["SQL", "Python", "Data Science", "BigQuery", "Statistics"],
            "location": "Bangalore",
            "work_mode": "hybrid",
            "salary_range": "15 LPA - 28 LPA",
            "experience_required": "0-1 years",
            "url": "https://careers.google.com/jobs/",
        },
    ],
    "Amazon Development Center": [
        {
            "title": "Backend Developer (AWS/Node.js)",
            "description": "Build microservices that power Amazon's e-commerce platform. Experience with Lambda, DynamoDB preferred.",
            "skills_required": ["Node.js", "AWS", "MongoDB", "Docker", "REST APIs", "JavaScript"],
            "location": "Hyderabad",
            "work_mode": "hybrid",
            "salary_range": "18 LPA - 38 LPA",
            "experience_required": "0-2 years",
            "url": "https://amazon.jobs/",
        },
        {
            "title": "Full Stack Developer",
            "description": "Work across the entire stack to deliver features for Amazon Prime and Fire TV. React frontend, Java/Spring backend.",
            "skills_required": ["React", "Java", "Python", "AWS", "MongoDB", "Docker"],
            "location": "Bangalore",
            "work_mode": "onsite",
            "salary_range": "20 LPA - 40 LPA",
            "experience_required": "1-3 years",
            "url": "https://amazon.jobs/",
        },
        {
            "title": "DevOps Engineer",
            "description": "Maintain and scale CI/CD pipelines for Amazon's deployment infrastructure. Kubernetes, Terraform, Jenkins.",
            "skills_required": ["Kubernetes", "Docker", "AWS", "Terraform", "CI/CD", "Linux"],
            "location": "Hyderabad",
            "work_mode": "hybrid",
            "salary_range": "22 LPA - 42 LPA",
            "experience_required": "1-3 years",
            "url": "https://amazon.jobs/",
        },
        {
            "title": "iOS Developer (Swift/SwiftUI)",
            "description": "Build and maintain the Amazon Shopping iOS app. Experience with Swift and UIKit required.",
            "skills_required": ["Swift", "iOS", "SwiftUI", "REST APIs", "Git"],
            "location": "Bangalore",
            "work_mode": "remote",
            "salary_range": "20 LPA - 35 LPA",
            "experience_required": "0-2 years",
            "url": "https://amazon.jobs/",
        },
        {
            "title": "QA Automation Engineer",
            "description": "Ensure product quality through automated testing. Selenium, Cypress, and Python test frameworks.",
            "skills_required": ["Python", "Selenium", "REST APIs", "CI/CD", "Java"],
            "location": "Hyderabad",
            "work_mode": "onsite",
            "salary_range": "12 LPA - 22 LPA",
            "experience_required": "0-1 years",
            "url": "https://amazon.jobs/",
        },
    ],
    "Infosys BPM": [
        {
            "title": "Python Developer (Fresher)",
            "description": "Join our Technology practice as a Python developer. Training provided. Work on enterprise automation solutions.",
            "skills_required": ["Python", "SQL", "REST APIs", "Git", "Linux"],
            "location": "Pune",
            "work_mode": "onsite",
            "salary_range": "4.5 LPA - 7 LPA",
            "experience_required": "0-1 years",
            "url": "https://www.infosys.com/careers/",
        },
        {
            "title": "React Developer (Fresher)",
            "description": "Build modern React applications for banking and financial clients. Classroom training in Mysore for 6 months.",
            "skills_required": ["React", "JavaScript", "HTML", "CSS", "REST APIs"],
            "location": "Mysore",
            "work_mode": "onsite",
            "salary_range": "4.5 LPA - 7 LPA",
            "experience_required": "0-1 years",
            "url": "https://www.infosys.com/careers/",
        },
        {
            "title": "Data Science Analyst",
            "description": "Support analytics initiatives for retail and healthcare clients using Python and ML frameworks.",
            "skills_required": ["Python", "Machine Learning", "Data Science", "SQL", "Excel"],
            "location": "Bangalore",
            "work_mode": "hybrid",
            "salary_range": "6 LPA - 12 LPA",
            "experience_required": "0-2 years",
            "url": "https://www.infosys.com/careers/",
        },
        {
            "title": "Java/Spring Boot Developer",
            "description": "Work on enterprise Java applications for banking clients. Spring Boot, Hibernate, REST APIs.",
            "skills_required": ["Java", "Spring Boot", "SQL", "REST APIs", "Maven"],
            "location": "Pune",
            "work_mode": "hybrid",
            "salary_range": "6 LPA - 14 LPA",
            "experience_required": "0-2 years",
            "url": "https://www.infosys.com/careers/",
        },
        {
            "title": "Cloud Engineer (AWS Fresher)",
            "description": "Learn cloud engineering on AWS. Assist in cloud migration projects for Fortune 500 clients.",
            "skills_required": ["AWS", "Python", "Linux", "Docker", "Networking"],
            "location": "Bangalore",
            "work_mode": "hybrid",
            "salary_range": "5 LPA - 10 LPA",
            "experience_required": "0-1 years",
            "url": "https://www.infosys.com/careers/",
        },
    ],
}

# ─────────── Default pipeline stages ───────────────────────────
def make_pipeline_stages():
    """Returns fresh pipeline stages with unique UUIDs."""
    applied_id   = str(uuid.uuid4())
    screening_id = str(uuid.uuid4())
    interview_id = str(uuid.uuid4())
    offer_id     = str(uuid.uuid4())
    hired_id     = str(uuid.uuid4())
    rejected_id  = str(uuid.uuid4())
    withdrawn_id = str(uuid.uuid4())

    stages = [
        {"id": applied_id,   "name": "Applied",          "order": 1, "type": "applied",    "color": "#3b82f6", "student_visible_name": "Application Received"},
        {"id": screening_id, "name": "Resume Screening", "order": 2, "type": "screening",  "color": "#8b5cf6", "student_visible_name": "Under Review"},
        {"id": interview_id, "name": "Phone Interview",  "order": 3, "type": "interview",  "color": "#06b6d4", "student_visible_name": "Interview Scheduled"},
        {"id": offer_id,     "name": "Offer Extended",   "order": 4, "type": "offer",      "color": "#ec4899", "student_visible_name": "Offer Received"},
        {"id": hired_id,     "name": "Hired",            "order": 5, "type": "hired",      "color": "#22c55e", "student_visible_name": "Hired"},
        {"id": rejected_id,  "name": "Rejected",         "order": 6, "type": "rejected",   "color": "#ef4444", "student_visible_name": "Not Selected"},
        {"id": withdrawn_id, "name": "Withdrawn",        "order": 7, "type": "withdrawn",  "color": "#6b7280", "student_visible_name": "Withdrawn"},
    ]
    transitions = [
        {"from_stage_id": applied_id,   "to_stage_id": screening_id, "allowed_by": ["recruiter"]},
        {"from_stage_id": screening_id, "to_stage_id": interview_id, "allowed_by": ["recruiter"]},
        {"from_stage_id": interview_id, "to_stage_id": offer_id,     "allowed_by": ["recruiter"]},
        {"from_stage_id": offer_id,     "to_stage_id": hired_id,     "allowed_by": ["recruiter"]},
        # Reject from any
        {"from_stage_id": applied_id,   "to_stage_id": rejected_id,  "allowed_by": ["recruiter"]},
        {"from_stage_id": screening_id, "to_stage_id": rejected_id,  "allowed_by": ["recruiter"]},
        {"from_stage_id": interview_id, "to_stage_id": rejected_id,  "allowed_by": ["recruiter"]},
        # Withdraw
        {"from_stage_id": applied_id,   "to_stage_id": withdrawn_id, "allowed_by": ["student"]},
        {"from_stage_id": screening_id, "to_stage_id": withdrawn_id, "allowed_by": ["student"]},
    ]
    return stages, transitions, applied_id, interview_id


# ─────────────────────────── Main seeding ──────────────────────
async def seed():
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    # ── 1. Find / verify student ────────────────────────────────
    print(f"\n[1] Looking for student: {STUDENT_EMAIL}")
    student = await db.users.find_one({"email": STUDENT_EMAIL})
    if not student:
        print(f"  Student {STUDENT_EMAIL} not found! Aborting — please register first.")
        client.close()
        return
    student_id = student["_id"]
    print(f"  Found student: {student.get('full_name') or student.get('username')} ({student_id})")

    # Update student skills to match job requirements
    await db.users.update_one({"_id": student_id}, {"$set": {
        "skills": [
            {"name": "python",           "level": 80, "proficiency": "Intermediate", "confidence": 85, "evidence": [], "last_updated": NOW},
            {"name": "react",            "level": 70, "proficiency": "Intermediate", "confidence": 75, "evidence": [], "last_updated": NOW},
            {"name": "javascript",       "level": 75, "proficiency": "Intermediate", "confidence": 80, "evidence": [], "last_updated": NOW},
            {"name": "machine learning", "level": 65, "proficiency": "Beginner",     "confidence": 60, "evidence": [], "last_updated": NOW},
            {"name": "aws",              "level": 55, "proficiency": "Beginner",     "confidence": 55, "evidence": [], "last_updated": NOW},
            {"name": "docker",           "level": 60, "proficiency": "Intermediate", "confidence": 65, "evidence": [], "last_updated": NOW},
            {"name": "sql",              "level": 70, "proficiency": "Intermediate", "confidence": 75, "evidence": [], "last_updated": NOW},
            {"name": "node.js",          "level": 60, "proficiency": "Beginner",     "confidence": 60, "evidence": [], "last_updated": NOW},
        ],
        "ai_profile": {
            "overall_score": 72,
            "skill_score": 75,
            "learning_score": 68,
            "interview_score": 70,
            "activity_score": 65,
            "profile_completeness": 90,
            "last_computed_at": NOW,
        },
        "updated_at": NOW
    }})
    print("  Updated student skills (Python, React, ML, AWS, Docker, SQL)")

    # ── 2. Create / fetch recruiters + pipelines ─────────────────
    print("\n[2] Creating recruiters and pipeline templates...")
    recruiter_docs = []

    for r_data in RECRUITERS:
        r = await db.users.find_one({"email": r_data["email"]})
        if not r:
            doc = {k: v for k, v in r_data.items() if k != "password"}
            doc["password_hash"] = hp(r_data["password"])
            doc["created_at"] = NOW
            doc["updated_at"] = NOW
            result = await db.users.insert_one(doc)
            r = await db.users.find_one({"_id": result.inserted_id})
            print(f"  Created recruiter: {r_data['company_name']} ({result.inserted_id})")
        else:
            print(f"  Recruiter exists: {r_data['company_name']} ({r['_id']})")

        # Ensure pipeline template exists
        pipeline = await db.pipeline_templates.find_one({"company_id": r["_id"], "active": True})
        if not pipeline:
            stages, transitions, applied_id, interview_id = make_pipeline_stages()
            pipeline_doc = {
                "company_id": r["_id"],
                "company_name": r["company_name"],
                "name": "Default Hiring Pipeline",
                "version": 1,
                "active": True,
                "is_default": True,
                "stages": stages,
                "transitions": transitions,
                "created_at": NOW,
                "updated_at": NOW,
                "created_by": r["_id"],
            }
            res = await db.pipeline_templates.insert_one(pipeline_doc)
            pipeline = await db.pipeline_templates.find_one({"_id": res.inserted_id})
            print(f"  Created pipeline for {r['company_name']}")
        
        recruiter_docs.append({"user": r, "pipeline": pipeline})

    # ── 3. Create jobs ───────────────────────────────────────────
    print("\n[3] Creating jobs...")
    recruiter_job_map = {}  # company_name -> list of job docs

    for rd in recruiter_docs:
        rec = rd["user"]
        company_name = rec["company_name"]
        jobs_list = JOBS_PER_RECRUITER.get(company_name, [])

        recruiter_job_map[company_name] = []
        for jd in jobs_list:
            existing = await db.jobs.find_one({
                "recruiter_id": rec["_id"],
                "title": jd["title"]
            })
            if existing:
                print(f"  Job exists: {jd['title']}")
                recruiter_job_map[company_name].append(existing)
            else:
                job_doc = {
                    **jd,
                    "recruiter_id": rec["_id"],
                    "company_name": company_name,
                    "visibility": "public",
                    "type": "Full-time",
                    "created_at": NOW - timedelta(days=5),
                    "updated_at": NOW,
                }
                res = await db.jobs.insert_one(job_doc)
                job = await db.jobs.find_one({"_id": res.inserted_id})
                recruiter_job_map[company_name].append(job)
                print(f"  Created job: {jd['title']} @ {company_name}")

    # ── 4. Create applications (student → 1st job at each company) ─
    print("\n[4] Creating applications...")
    application_docs = []

    for rd in recruiter_docs:
        rec = rd["user"]
        pipeline = rd["pipeline"]
        company_name = rec["company_name"]
        jobs = recruiter_job_map.get(company_name, [])
        if not jobs:
            continue
        target_job = jobs[0]  # apply to first job at each company

        # Check existing application
        existing_app = await db.applications.find_one({
            "job_id": target_job["_id"],
            "student_id": student_id
        })
        if existing_app:
            print(f"  Application exists: {target_job['title']} @ {company_name}")
            application_docs.append({"app": existing_app, "recruiter": rec, "job": target_job, "pipeline": pipeline})
            continue

        # Find applied stage
        applied_stage = next((s for s in pipeline["stages"] if s["type"] == "applied"), None)
        if not applied_stage:
            print(f"  WARNING: No 'applied' stage in pipeline for {company_name}!")
            continue

        applied_at = NOW - timedelta(days=3)
        app_doc = {
            "job_id": target_job["_id"],
            "student_id": student_id,
            "company_id": rec["_id"],
            "pipeline_template_id": pipeline["_id"],
            "pipeline_version": pipeline.get("version", 1),
            "current_stage_id": applied_stage["id"],
            "current_stage_name": applied_stage["name"],
            "student_visible_stage": "Application Received",
            "status": "active",
            "stage_history": [
                {
                    "stage_id": applied_stage["id"],
                    "stage_name": applied_stage["name"],
                    "changed_by": str(student_id),
                    "timestamp": applied_at,
                    "reason": "Initial application submitted"
                }
            ],
            "thread_id": None,
            "interview_ids": [],
            "offer_id": None,
            "notes": [],
            "tags": ["strong_candidate", "python"],
            "rating_summary": {"overall_score": None, "scorecard_count": 0, "last_updated": None},
            "applied_at": applied_at,
            "created_at": applied_at,
            "updated_at": applied_at,
        }
        res = await db.applications.insert_one(app_doc)
        app = await db.applications.find_one({"_id": res.inserted_id})
        application_docs.append({"app": app, "recruiter": rec, "job": target_job, "pipeline": pipeline})
        print(f"  Created application: {target_job['title']} @ {company_name}")

    # ── 5. Create message threads ─────────────────────────────────
    print("\n[5] Creating message threads...")
    thread_ids = []

    for item in application_docs:
        rec = item["recruiter"]
        job = item["job"]
        app = item["app"]

        # Check existing thread using participant_hash (unique index)
        p_hash = "|".join(sorted([str(student_id), str(rec["_id"])]))
        existing_thread = await db.threads.find_one({"participant_hash": p_hash})
        if existing_thread:
            print(f"  Thread exists: student <-> {rec['company_name']}")
            thread_ids.append(str(existing_thread["_id"]))
            # Link thread to application
            await db.applications.update_one({"_id": app["_id"]}, {"$set": {"thread_id": existing_thread["_id"]}})
            continue

        # Create thread — participant_hash is required by unique index
        p_hash = "|".join(sorted([str(student_id), str(rec["_id"])]))
        thread_created_at = NOW - timedelta(days=2, hours=3)
        thread_doc = {
            "participants": [student_id, rec["_id"]],
            "participant_hash": p_hash,
            "participant_info": [
                {
                    "id": student_id,
                    "username": student.get("username"),
                    "full_name": student.get("full_name") or student.get("username"),
                    "avatar_url": student.get("avatar_url", ""),
                    "role": "student"
                },
                {
                    "id": rec["_id"],
                    "username": rec.get("username"),
                    "full_name": rec.get("full_name") or rec.get("company_name"),
                    "avatar_url": rec.get("avatar_url", ""),
                    "role": "recruiter"
                }
            ],
            "job_id": job["_id"],
            "created_at": thread_created_at,
            "updated_at": thread_created_at,
            "last_message_at": thread_created_at,
            "last_message_preview": f"Hi {student.get('full_name', 'there')}, we reviewed your application...",
            "unread_counts": {str(student_id): 1, str(rec["_id"]): 0},
            "messages": []
        }
        t_res = await db.threads.insert_one(thread_doc)
        thread_id = t_res.inserted_id
        thread_ids.append(str(thread_id))
        
        # Link thread to application
        await db.applications.update_one({"_id": app["_id"]}, {"$set": {"thread_id": thread_id}})

        # Seed messages using the real messages collection schema (thread_id, sender_id, text, read_by)
        student_name = student.get("full_name") or student.get("username") or "Sushant"
        rec_name = rec.get("full_name") or rec.get("company_name")
        messages = [
            {
                "_id": ObjectId(),
                "thread_id": thread_id,
                "sender_id": rec["_id"],
                "text": (
                    f"Hi {student_name}! 👋 I'm {rec_name} from {rec['company_name']}. "
                    f"We reviewed your application for the {job['title']} role and are very impressed with your background. "
                    f"Would you be available for a quick 30-minute introductory call this week?"
                ),
                "read_by": [rec["_id"], student_id],  # student has read it
                "created_at": NOW - timedelta(days=2, hours=2),
            },
            {
                "_id": ObjectId(),
                "thread_id": thread_id,
                "sender_id": student_id,
                "text": (
                    f"Hi {rec_name}! Thank you so much for reaching out — I'm really excited about this opportunity at {rec['company_name']}! "
                    f"Yes, I'm available this week. I can do Thursday or Friday afternoon (2-6 PM IST). "
                    f"Please let me know what works best for your team. Looking forward to speaking with you!"
                ),
                "read_by": [student_id, rec["_id"]],
                "created_at": NOW - timedelta(days=1, hours=18),
            },
            {
                "_id": ObjectId(),
                "thread_id": thread_id,
                "sender_id": rec["_id"],
                "text": (
                    f"Great to hear that, {student_name}! Let's go with Thursday at 4 PM IST. "
                    f"I'll send a calendar invite shortly with the video call link. "
                    f"Please have your resume and GitHub ready. See you then!"
                ),
                "read_by": [rec["_id"]],  # student hasn't read this yet
                "created_at": NOW - timedelta(hours=6),
            },
        ]
        # Insert messages into a 'messages' collection
        await db.messages.insert_many(messages)
        # Update thread with last message info
        await db.threads.update_one({"_id": thread_id}, {"$set": {
            "last_message_at": messages[-1]["created_at"],
            "last_message_preview": messages[-1]["text"][:80] + "...",
            "unread_counts": {str(student_id): 1, str(rec["_id"]): 0},
            "updated_at": messages[-1]["created_at"]
        }})
        print(f"  Created thread + 3 messages: student <-> {rec['company_name']}")

    # ── 6. Create interviews ──────────────────────────────────────
    print("\n[6] Creating scheduled interviews...")
    interview_days_offset = [3, 5, 7]

    for idx, item in enumerate(application_docs):
        rec = item["recruiter"]
        job = item["job"]
        app = item["app"]
        pipeline = item["pipeline"]

        interview_stage = next((s for s in pipeline["stages"] if s["type"] == "interview"), None)
        if not interview_stage:
            print(f"  WARNING: No interview stage for {rec['company_name']}")
            continue

        # Check existing interview
        existing_iv = await db.interviews.find_one({
            "candidate_id": student_id,
            "recruiter_id": rec["_id"],
            "job_id": job["_id"]
        })
        if existing_iv:
            print(f"  Interview exists: student <-> {rec['company_name']}")
            continue

        # Build scheduled slot
        interview_date = NOW + timedelta(days=interview_days_offset[idx])
        slot_start = interview_date.replace(hour=10, minute=30, second=0, microsecond=0)
        slot_end = slot_start + timedelta(minutes=45)
        slot = {
            "start": slot_start,
            "end": slot_end,
            "timezone": "Asia/Kolkata"
        }

        interview_doc = {
            "candidate_id": student_id,
            "recruiter_id": rec["_id"],
            "job_id": job["_id"],
            "thread_id": None,
            "proposed_by": rec["_id"],
            "proposed_times": [slot],
            "scheduled_slot": slot,   # auto-accepted
            "location": {
                "type": "video",
                "url": "https://meet.google.com/studenthub-demo",
                "address": None
            },
            "status": "scheduled",
            "description": (
                f"Interview for {job['title']} at {rec['company_name']}. "
                f"Please prepare: (1) Introduction, (2) 2 project deep-dives, (3) DSA question."
            ),
            "feedback": [],
            "history": [
                {
                    "event": "proposed",
                    "by": str(rec["_id"]),
                    "at": NOW - timedelta(days=1),
                    "data": {"times": [slot]}
                },
                {
                    "event": "accepted",
                    "by": str(student_id),
                    "at": NOW - timedelta(hours=12),
                    "data": {"slot": slot}
                }
            ],
            "created_at": NOW - timedelta(days=1),
            "updated_at": NOW - timedelta(hours=12),
        }
        iv_res = await db.interviews.insert_one(interview_doc)
        interview_id = iv_res.inserted_id
        print(f"  Created interview: {rec['company_name']} on {slot_start.strftime('%Y-%m-%d %H:%M')} IST")

        # Link interview to application + advance stage
        await db.applications.update_one(
            {"_id": app["_id"]},
            {
                "$addToSet": {"interview_ids": interview_id},
                "$set": {
                    "current_stage_id": interview_stage["id"],
                    "current_stage_name": interview_stage["name"],
                    "student_visible_stage": "Interview Scheduled",
                    "updated_at": NOW
                },
                "$push": {
                    "stage_history": {
                        "stage_id": interview_stage["id"],
                        "stage_name": interview_stage["name"],
                        "changed_by": str(rec["_id"]),
                        "timestamp": NOW - timedelta(hours=10),
                        "reason": "Interview scheduled"
                    }
                }
            }
        )

        # Create notification for student
        await db.notifications.insert_one({
            "user_id": student_id,
            "kind": "interview_proposed",
            "category": "interview",
            "priority": "high",
            "is_read": False,
            "payload": {
                "interview_id": str(interview_id),
                "job_title": job["title"],
                "company": rec["company_name"],
                "date": slot_start.isoformat(),
            },
            "created_at": NOW - timedelta(hours=12),
            "updated_at": NOW - timedelta(hours=12),
        })

    # ── 7. Create application notifications ────────────────────────
    print("\n[7] Creating application-received notifications...")
    for item in application_docs:
        rec = item["recruiter"]
        job = item["job"]
        existing = await db.notifications.find_one({
            "user_id": student_id,
            "kind": "application_received",
            "payload.job_title": job["title"]
        })
        if not existing:
            await db.notifications.insert_one({
                "user_id": student_id,
                "kind": "application_received",
                "category": "jobs",
                "priority": "medium",
                "is_read": False,
                "payload": {
                    "job_title": job["title"],
                    "company": rec["company_name"],
                },
                "created_at": NOW - timedelta(days=3),
                "updated_at": NOW - timedelta(days=3),
            })
            print(f"  Notification: Application received for {job['title']} @ {rec['company_name']}")

    print("\n✅ Seeding complete!")
    print("\nCredentials summary:")
    print(f"  STUDENT:  {STUDENT_EMAIL} / Sushant@512")
    for r in RECRUITERS:
        print(f"  RECRUITER ({r['company_name']}): {r['email']} / {r['password']}")
    print("\nStudent now has:")
    print("  • 3 active applications (one per company)")
    print("  • 3 message threads with recruiters (3 messages each)")
    print("  • 3 scheduled interviews (3, 5, 7 days from now)")
    print("  • 5 notifications (3 interview, 3 application-received)")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
