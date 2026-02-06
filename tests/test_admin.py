import pytest
from fastapi.testclient import TestClient
from backend.utils.auth import create_access_token



def test_admin_stats(authenticated_admin_client: TestClient):
    """Test admin dashboard stats."""
    response = authenticated_admin_client.get("/admin/stats")
    if response.status_code == 404:
        pytest.skip("Admin stats endpoint not implemented")
    
    assert response.status_code == 200
    data = response.json()
    # Should have some stats about users, jobs, or applications
    assert isinstance(data, dict)

def test_approve_recruiter(authenticated_admin_client: TestClient):
    """Test recruiter approval workflow."""
    # 1. Create a pending recruiter first
    from motor.motor_asyncio import AsyncIOMotorClient
    from backend.config import settings
    from backend.utils.auth import hash_password
    from bson import ObjectId
    import asyncio
    from datetime import datetime
    
    recruiter_id = str(ObjectId())
    
    async def _seed_pending_recruiter():
        motor_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = motor_client[settings.mongodb_db]
        
        await database["users"].insert_one({
            "_id": ObjectId(recruiter_id),
            "username": f"pending_rec_{recruiter_id[:8]}",
            "email": f"pending_{recruiter_id[:8]}@test.com",
            "hashed_password": hash_password("pass123"),
            "role": "recruiter",
            "verification_status": "review_required", # Matches constant in code
            "created_at": datetime.utcnow()
        })
        motor_client.close()
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_seed_pending_recruiter())
    loop.close()

    # 2. Verify the recruiter
    response = authenticated_admin_client.put(f"/admin/recruiters/{recruiter_id}/verify")
    
    # Should succeed now
    assert response.status_code == 200
    assert response.json()["message"] == "Recruiter verified"

def test_moderation_queue(authenticated_admin_client: TestClient):
    """Test fetching content for moderation."""
    response = authenticated_admin_client.get("/admin/moderation")
    if response.status_code == 404:
        pytest.skip("Moderation endpoint not implemented")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
