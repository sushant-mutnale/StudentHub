from datetime import datetime, timedelta, timezone

from .database import get_database
from .utils.auth import hash_password


async def seed_default_users():
    db = get_database()
    if await db["users"].count_documents({}) > 3:
        return
    now = datetime.now(timezone.utc)

    demo_users = [
        {
            "role": "student",
            "username": "demo_student",
            "email": "student@example.com",
            "password_hash": hash_password("Student@123"),
            "full_name": "Demo Student",
            "prn": "PRN00123",
            "college": "Sample University",
            "branch": "Computer Science",
            "year": "3rd Year",
            "skills": ["React", "Python", "MongoDB"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "alice_coder",
            "email": "alice@example.com",
            "password_hash": hash_password("Alice@123"),
            "full_name": "Alice Johnson",
            "prn": "PRN00456",
            "college": "Sample University",
            "branch": "Computer Science",
            "year": "3rd Year",
            "skills": ["React", "JavaScript", "UI Design"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "bob_data",
            "email": "bob@example.com",
            "password_hash": hash_password("Bob@123"),
            "full_name": "Bob Smith",
            "prn": "PRN00789",
            "college": "Tech Institute",
            "branch": "IT",
            "year": "2nd Year",
            "skills": ["Python", "SQL", "Data Science"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "charlie_dev",
            "email": "charlie@example.com",
            "password_hash": hash_password("Charlie@123"),
            "full_name": "Charlie Brown",
            "prn": "PRN00111",
            "college": "Sample University",
            "branch": "Data Science",
            "year": "4th Year",
            "skills": ["Python", "Machine Learning", "FastAPI"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "recruiter",
            "username": "demo_recruiter",
            "email": "recruiter@example.com",
            "password_hash": hash_password("Recruiter@123"),
            "company_name": "Talent Seekers",
            "contact_number": "+1-555-0101",
            "website": "https://talentseekers.example.com",
            "company_description": "Connecting graduates with dream jobs.",
            "skills": [],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
    ]

    for user in demo_users:
        if not await db["users"].find_one({"username": user["username"]}):
            await db["users"].insert_one(user)

    if await db["opportunities_hackathons"].count_documents({}) == 0:
        await db["opportunities_hackathons"].insert_many(
            [
                {
                    "source": "seed",
                    "source_id": "seed_h1",
                    "event_url": "https://devpost.com/hackathons",
                    "event_name": "Global AI Challenge 2026",
                    "organizer": "Google Cloud",
                    "theme_tags": ["AI", "ML", "Cloud"],
                    "start_date": now + timedelta(days=20),
                    "status": "open",
                },
                {
                    "source": "seed",
                    "source_id": "seed_h2",
                    "event_url": "https://devpost.com/hackathons",
                    "event_name": "Web3 Innovation Summit",
                    "organizer": "Solana Foundation",
                    "theme_tags": ["Web3", "Blockchain"],
                    "start_date": now + timedelta(days=15),
                    "status": "upcoming",
                },
            ]
        )

    if await db["opportunities_content"].count_documents({}) == 0:
        await db["opportunities_content"].insert_many(
            [
                {
                    "source_id": "seed_r1",
                    "title": "Mastering React Server Components",
                    "publisher": "React Blog",
                    "topic": "Frontend",
                    "url": "https://react.dev/blog",
                    "published_at": now - timedelta(days=2),
                },
                {
                    "source_id": "seed_r2",
                    "title": "System Design: The Complete Guide",
                    "publisher": "Medium",
                    "topic": "Architecture",
                    "url": "https://medium.com",
                    "published_at": now - timedelta(days=5),
                },
            ]
        )
