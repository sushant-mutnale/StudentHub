"""
Shared test fixtures for StudentHub backend tests.
Provides test app, authenticated tokens, and seed data.

Uses asgi-lifespan to properly trigger FastAPI startup/shutdown events,
ensuring DB connection and other initializations work correctly.
"""

import os
from datetime import datetime

import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

# Force testing mode BEFORE importing app
os.environ["APP_ENV"] = "testing"
os.environ["MONGODB_DB"] = "student_hub_test"

from backend.main import app
from backend.database import get_database
from backend.utils.auth import hash_password, create_access_token


# ---------- App + DB Lifecycle ----------

@pytest_asyncio.fixture(scope="session")
async def managed_app():
    """
    Start the FastAPI app with full lifespan (startup + shutdown).
    This ensures connect_to_mongo() runs before any test.
    Timeout raised because cloud Atlas + index creation can be slow.
    """
    async with LifespanManager(app, startup_timeout=30, shutdown_timeout=30) as manager:
        yield manager.app


@pytest_asyncio.fixture(autouse=True)
async def clean_collections(managed_app):
    """Clean relevant collections before each test."""
    test_db = get_database()
    collections_to_clean = [
        "users", "jobs", "interviews", "interview_sessions",
        "session_questions", "session_answers", "posts",
        "notifications", "activities", "outbox_events",
        "multi_agent_sessions", "opportunities_jobs",
    ]
    for col in collections_to_clean:
        await test_db[col].delete_many({})
    yield


# ---------- Seed Data ----------

@pytest_asyncio.fixture
async def student_user(managed_app):
    """Insert and return a test student user."""
    test_db = get_database()
    now = datetime.utcnow()
    user = {
        "_id": ObjectId(),
        "role": "student",
        "username": "test_student",
        "email": "student@test.com",
        "password_hash": hash_password("Test@123"),
        "full_name": "Test Student",
        "prn": "PRN001",
        "college": "Test University",
        "branch": "Computer Science",
        "year": "3rd Year",
        "skills": ["Python", "React", "MongoDB"],
        "created_at": now,
        "updated_at": now,
    }
    await test_db["users"].insert_one(user)
    return user


@pytest_asyncio.fixture
async def recruiter_user(managed_app):
    """Insert and return a test recruiter user."""
    test_db = get_database()
    now = datetime.utcnow()
    user = {
        "_id": ObjectId(),
        "role": "recruiter",
        "username": "test_recruiter",
        "email": "recruiter@test.com",
        "password_hash": hash_password("Test@123"),
        "company_name": "Test Corp",
        "contact_number": "+1-555-0100",
        "website": "https://testcorp.example.com",
        "skills": [],
        "created_at": now,
        "updated_at": now,
    }
    await test_db["users"].insert_one(user)
    return user


@pytest_asyncio.fixture
async def test_job(recruiter_user, managed_app):
    """Insert and return a test job posting."""
    test_db = get_database()
    now = datetime.utcnow()
    job = {
        "_id": ObjectId(),
        "title": "Software Engineer",
        "description": "Build scalable backend services with Python and FastAPI.",
        "company_name": recruiter_user["company_name"],
        "recruiter_id": recruiter_user["_id"],
        "location": "Remote",
        "type": "Full-time",
        "salary_range": "$80k - $120k",
        "skills_required": ["Python", "FastAPI", "MongoDB"],
        "created_at": now,
        "updated_at": now,
    }
    await test_db["jobs"].insert_one(job)
    return job


# ---------- Auth Helpers ----------

def make_token(user: dict) -> str:
    """Create a JWT token for a user."""
    token, _ = create_access_token(data={"sub": str(user["_id"])})
    return token


def auth_headers(token: str) -> dict:
    """Build Authorization header."""
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def student_token(student_user):
    return make_token(student_user)


@pytest_asyncio.fixture
async def recruiter_token(recruiter_user):
    return make_token(recruiter_user)


# ---------- HTTP Client ----------

@pytest_asyncio.fixture
async def client(managed_app):
    """Async HTTP client bound to the lifespan-managed app."""
    transport = ASGITransport(app=managed_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
