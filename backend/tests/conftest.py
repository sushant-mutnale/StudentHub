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

# Force LOCAL Redis for hermetic tests (see root tests/conftest.py)
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "6380"
os.environ["REDIS_USERNAME"] = ""
os.environ["REDIS_PASSWORD"] = ""
os.environ["REDIS_SSL"] = "false"

from backend.main import app
from backend.config import settings
from backend.database import get_database
from backend.utils.auth import hash_password, create_access_token

# Force settings to use local ephemeral infra (never the developer's cloud)
settings.app_env = "testing"
settings.mongodb_db = "student_hub_test"
settings.mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
settings.redis_host = os.environ["REDIS_HOST"]
settings.redis_port = int(os.environ["REDIS_PORT"])
settings.redis_username = os.environ["REDIS_USERNAME"]
settings.redis_password = os.environ["REDIS_PASSWORD"]
settings.redis_ssl = False


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
    """Clean relevant collections and all caches before each test."""
    test_db = get_database()
    collections_to_clean = [
        "users", "jobs", "interviews", "interview_sessions",
        "session_questions", "session_answers", "posts",
        "notifications", "activities", "outbox_events",
        "multi_agent_sessions", "opportunities_jobs",
        "resume_uploads", "resume_cache",
        "saved_searches", "saved_jobs", "recommendation_feedback",
    ]
    for col in collections_to_clean:
        await test_db[col].delete_many({})
    # Clear application-level cache (Redis + in-memory fallback)
    try:
        from backend.services.cache_service import cache
        await cache.clear()
    except Exception:
        pass
    # Also flush Redis directly for non-cache keys
    try:
        from backend.redis_client import get_redis
        redis = get_redis()
        await redis.flushdb()
    except Exception:
        pass
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
