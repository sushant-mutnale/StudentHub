from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import close_mongo_connection, connect_to_mongo, get_database
from .models.indexes import ensure_database_indexes
from .routes import (
    auth_routes,
    interview_routes,
    job_routes,
    match_routes,
    offer_routes,
    post_routes,
    thread_routes,
    user_routes,
)
from .utils.auth import hash_password

app = FastAPI(title="Student Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await ensure_database_indexes()
    if settings.app_env.lower() != "production":
        await seed_default_users()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(post_routes.router, prefix="/posts", tags=["posts"])
app.include_router(job_routes.router, prefix="/jobs", tags=["jobs"])
app.include_router(match_routes.router, prefix="/jobs", tags=["matches"])
app.include_router(thread_routes.router, tags=["threads"])
app.include_router(interview_routes.router)
app.include_router(offer_routes.router)


async def seed_default_users():
    db = get_database()
    if await db["users"].count_documents({}) > 0:
        return
    now = datetime.utcnow()
    await db["users"].insert_many(
        [
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
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

