
import asyncio
import os
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from passlib.context import CryptContext

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://Sush_512:Sushant%40512@studenthub.zlkxvkr.mongodb.net/?appName=Studenthub")
DB_NAME = os.getenv("MONGODB_DB", "student_hub")

# Use same config as backend/utils/auth.py
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=390000,
)

def hash_password(password: str):
    return pwd_context.hash(password)

# Mock Data
SKILLS_POOL = [
    "Python", "JavaScript", "React", "Node.js", "MongoDB", "AWS", 
    "Machine Learning", "Data Science", "C++", "Java", "Docker", 
    "Kubernetes", "Figma", "UI/UX", "Flutter"
]

INTERESTS_POOL = [
    "Web Development", "AI/ML", "Cloud Computing", "App Development", 
    "BlockChain", "Cybersecurity", "Game Development"
]

RECRUITER_DATA = {
    "username": "techcorp_recruiter",
    "email": "careers@techcorp.com",
    "password": "password123",
    "role": "recruiter",
    "company_name": "TechCorp Solutions",
    "full_name": "TechCorp Recruiter",
    "contact_number": "9876543210",
    "website": "https://techcorp.com",
    "company_description": "Leading innovator in AI and Cloud solutions.",
    "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=TC",
    "location": "Bangalore"
}

JOB_TITLES = [
    "Junior Python Developer", "Frontend Engineer (React)", "Backend Developer (Node.js)",
    "Full Stack Developer", "Data Scientist Intern", "Machine Learning Engineer",
    "DevOps Engineer", "Cloud Architect", "UI/UX Designer", "Product Manager Intern",
    "Mobile App Developer (Flutter)", "QA Automation Engineer", "Cybersecurity Analyst",
    "Blockchain Developer", "Technical Content Writer"
]

POST_TEMPLATES = [
    "Just finished a great project on {topic}! Check it out on my GitHub.",
    "Excited to start learning {topic}. Any resources recommended?",
    "Attended a webinar on {topic} today. Totally mind-blowing!",
    "Looking for teammates for a hackathon. We need someone good with {topic}.",
    "Finally solved that bug in my {topic} project. Debugging is pain but satisfaction!",
    "Does anyone know how to integrate {topic} with MongoDB?",
    "Just earned a certification in {topic}! Feeling proud.",
    "Thinking about building a startup around {topic}. Thoughts?",
    "Why is {topic} so complicated sometimes? ugh.",
    "Love how {topic} is changing the tech landscape."
]

async def seed_data():
    print(f"Connecting to {MONGODB_URI}...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    # 1. Create Recruiter
    print("Creating Recruiter...")
    recruiter = await db.users.find_one({"email": RECRUITER_DATA["email"]})
    if not recruiter:
        recruiter_doc = RECRUITER_DATA.copy()
        recruiter_doc["password_hash"] = hash_password(recruiter_doc.pop("password"))
        recruiter_doc["created_at"] = datetime.utcnow()
        recruiter_doc["updated_at"] = datetime.utcnow()
        result = await db.users.insert_one(recruiter_doc)
        recruiter_id = result.inserted_id
        print(f"Created recruiter: {recruiter_id}")
    else:
        recruiter_id = recruiter["_id"]
        print(f"Recruiter already exists: {recruiter_id}")

    # 2. Create 15 Jobs
    print("Creating Jobs...")
    existing_jobs = await db.jobs.count_documents({"recruiter_id": recruiter_id})
    jobs_to_create = 15 - existing_jobs
    
    if jobs_to_create > 0:
        jobs = []
        for i in range(jobs_to_create):
            title = JOB_TITLES[i % len(JOB_TITLES)]
            skills = random.sample(SKILLS_POOL, k=random.randint(3, 6))
            job = {
                "recruiter_id": recruiter_id,
                "company_name": RECRUITER_DATA["company_name"],
                "title": title,
                "description": f"We are looking for a passionate {title} to join our team. Proficiency in {', '.join(skills)} is required.",
                "skills_required": skills,
                "location": random.choice(["Bangalore", "Mumbai", "Remote", "Delhi", "Hyderabad"]),
                "visibility": "public",
                "work_mode": random.choice(["onsite", "remote", "hybrid"]),
                "salary_range": "10LPA - 20LPA",
                "experience_required": random.choice(["0-1 years", "1-3 years", "3-5 years"]),
                "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                "updated_at": datetime.utcnow()
            }
            jobs.append(job)
        
        if jobs:
            await db.jobs.insert_many(jobs)
            print(f"Added {len(jobs)} jobs.")
    else:
        print("Jobs already seeded.")

    # 3. Create 10 Students and Posts
    print("Creating Students and Posts...")
    for i in range(1, 11):
        username = f"student_{i}"
        email = f"student_{i}@example.com"
        
        student = await db.users.find_one({"email": email})
        if not student:
            skills = []
            for s in random.sample(SKILLS_POOL, k=5):
                skills.append({
                    "name": s.lower(),
                    "level": random.randint(40, 90),
                    "proficiency": random.choice(["Beginner", "Intermediate", "Advanced"]),
                    "confidence": random.randint(50, 100),
                    "evidence": [],
                    "last_updated": datetime.utcnow()
                })
            
            student_doc = {
                "username": username,
                "email": email,
                "password_hash": hash_password("password123"),
                "role": "student",
                "full_name": f"Student {i}",
                "college": "Tech University",
                "branch": "Computer Science",
                "year": random.choice(["2nd Year", "3rd Year", "4th Year"]),
                "skills": skills,
                "interests": random.sample(INTERESTS_POOL, k=3),
                "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
                "bio": f"Passionate about technology and learning new things. Exploring {skills[0]['name']}.",
                "ai_profile": {
                    "overall_score": random.randint(50, 90),
                    "skill_score": random.randint(50, 90),
                    "learning_score": random.randint(50, 90),
                    "interview_score": random.randint(50, 90),
                    "activity_score": random.randint(50, 90),
                    "profile_completeness": 80,
                    "last_computed_at": datetime.utcnow()
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            res = await db.users.insert_one(student_doc)
            student_id = res.inserted_id
            print(f"Created student: {username}")
        else:
            student_id = student["_id"]
            print(f"Student already exists: {username}")

        # Create 2 Posts for this student
        posts_count = await db.posts.count_documents({"author_id": student_id})
        if posts_count < 2:
            posts = []
            for j in range(2):
                topic = random.choice(SKILLS_POOL)
                content = random.choice(POST_TEMPLATES).format(topic=topic)
                post = {
                    "author_id": student_id,
                    "author_name": f"Student {i}",
                    "author_username": username,
                    "author_role": "student",
                    "author_avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
                    "content": content,
                    "tags": [topic.lower(), "learning", "tech"],
                    "created_at": datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                    "updated_at": datetime.utcnow(),
                    "likes": [],
                    "comments": []
                }
                posts.append(post)
            
            await db.posts.insert_many(posts)
            print(f"Added 2 posts for {username}")

    print("Seeding completed successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
