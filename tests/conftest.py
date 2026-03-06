import asyncio
import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient

# Override env settings for testing
os.environ["APP_ENV"] = "testing"
os.environ["MONGODB_DB"] = "student_hub_test" 

from backend.main import app
from backend.database import db
from backend.config import settings

# FORCE SETTINGS UPDATE
# This ensures that even if config was imported before env vars were set,
# we explicitly point to the test environment.
settings.app_env = "testing"
settings.mongodb_db = "student_hub_test" 
# print(f"DEBUG_CONFTEST: Settings updated. DB={settings.mongodb_db}") 

from backend.utils.auth import create_access_token

fake = Faker()

# --- Database Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def test_db_lifecycle():
    """Ensure database connection exists for fixtures."""
    # We rely on TestClient to trigger app startup for the app's connection
    # But fixtures need a connection too.
    # We'll creating a temporary one for fixtures/cleanup.
    pass # Managed by app startup or manual client below

@pytest.fixture(scope="session", autouse=True)
def mock_otp_service():
    """Mock OTP service to allow signups without actual OTP verification."""
    from unittest.mock import AsyncMock, patch
    
    # Mock verify_otp to always return success
    async def mock_verify_otp(email, otp, purpose, consume=True):
        return True, "OTP verified (mocked)"
    
    # Mock generate_otp to return a fake OTP
    async def mock_generate_otp(email, purpose):
        return "123456"
    
    with patch("backend.services.otp_service.otp_service.verify_otp", new=mock_verify_otp):
        with patch("backend.services.otp_service.otp_service.generate_otp", new=mock_generate_otp):
            yield

@pytest.fixture(scope="function", autouse=True)
def clear_db():
    """Clean database between tests."""
    import asyncio
    
    async def _clear():
        client = AsyncIOMotorClient(settings.mongodb_uri)
        database = client[settings.mongodb_db]
        collections = await database.list_collection_names()
        for collection in collections:
            await database[collection].delete_many({})
        client.close()
        
    # Run sync
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_clear())
    loop.close()
    yield

# --- Client Fixture (Session-scoped to avoid loop conflicts) ---
@pytest.fixture(scope="session")
def _test_client() -> Generator[TestClient, None, None]:
    """Session-scoped TestClient to avoid multiple app lifecycle events."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def client(_test_client) -> TestClient:
    """Function-scoped alias that reuses session client."""
    # Reset headers for each test
    _test_client.headers = {}
    return _test_client

# --- Auth Fixtures (Synchronous) ---
# We need to insert data into DB for tokens.
# Since fixtures are synchronous now, we use a sync-to-async helper or direct Motor call via run_until_complete

@pytest.fixture
def student_token(client): # client unused but ensures app started
    """Create a student and return valid JWT."""
    from backend.utils.auth import hash_password
    import asyncio
    
    from datetime import datetime
    
    user_data = {
        "email": fake.email(),
        "username": fake.user_name(),
        "password": hash_password("pass123"),
        "role": "student",
        "full_name": fake.name(),
        "prn": "PRN123456",
        "college": "Test College",
        "branch": "Test Branch",
        "year": "2024",
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    async def _insert():
        motor_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = motor_client[settings.mongodb_db]
        result = await database["users"].insert_one(user_data)
        motor_client.close()
        return str(result.inserted_id)

    loop = asyncio.new_event_loop()
    user_id = loop.run_until_complete(_insert())
    loop.close()
    
    token, _ = create_access_token({"sub": user_id, "role": "student"})
    return token

@pytest.fixture
def recruiter_token(client):
    """Create a verified recruiter and return valid JWT."""
    from backend.utils.auth import hash_password
    import asyncio
    from datetime import datetime
    
    user_data = {
        "email": fake.email(),
        "username": fake.user_name(),
        "password": hash_password("RecruiterPass123!"),
        "role": "recruiter",
        "company_name": fake.company(),
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    async def _insert():
        motor_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = motor_client[settings.mongodb_db]
        result = await database["users"].insert_one(user_data)
        motor_client.close()
        return str(result.inserted_id)

    loop = asyncio.new_event_loop()
    user_id = loop.run_until_complete(_insert())
    loop.close()
    
    token, _ = create_access_token({"sub": user_id, "role": "recruiter"})
    return token

@pytest.fixture
def authenticated_student_client(client, student_token):
    """Return the shared TestClient with student auth headers."""
    client.headers = {"Authorization": f"Bearer {student_token}"}
    return client

@pytest.fixture
def authenticated_recruiter_client(client, recruiter_token):
    """Return the shared TestClient with recruiter auth headers."""
    client.headers = {"Authorization": f"Bearer {recruiter_token}"}
    return client

@pytest.fixture
def admin_token(client):
    """Create a seeded admin user and return valid JWT."""
    from backend.utils.auth import hash_password
    import asyncio
    from datetime import datetime
    from bson import ObjectId
    
    user_id = str(ObjectId())
    user_data = {
        "_id": ObjectId(user_id),
        "email": "admin@test.com",
        "username": "admin_test",
        "password": hash_password("AdminPass123!"),
        "role": "admin",
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    async def _insert():
        motor_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = motor_client[settings.mongodb_db]
        await database["users"].insert_one(user_data)
        motor_client.close()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_insert())
    loop.close()
    
    token, _ = create_access_token({"sub": user_id, "role": "admin"})
    return token

@pytest.fixture
def authenticated_admin_client(client, admin_token):
    """Return the shared TestClient with admin auth headers."""
    client.headers = {"Authorization": f"Bearer {admin_token}"}
    return client

# --- Data Fixtures ---
@pytest.fixture
def test_job(client, recruiter_token):
    """Create a sample job posting using explicit auth headers (doesn't mutate client)."""
    job_data = {
        "title": "Software Engineer Intern",
        "description": "Great opportunity",
        "location": "Remote",
        "type": "internship",
        "skills_required": ["Python", "React"],
        "salary_range": "$30-50k",
    }
    # Use explicit headers in this single request, don't mutate the client globally
    response = client.post(
        "/jobs/", 
        json=job_data,
        headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    if response.status_code == 201:
        return response.json()
    return {"error": response.text, "status": response.status_code}
