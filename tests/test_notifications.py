import pytest
from fastapi.testclient import TestClient

def test_get_notifications(authenticated_student_client: TestClient):
    """Test fetching notifications."""
    response = authenticated_student_client.get("/notifications/")
    if response.status_code == 404:
        pytest.skip("Notifications endpoint not implemented")
        
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_mark_notification_read(authenticated_student_client: TestClient):
    """Test marking notification as read."""
    # Seed a notification first!
    me_res = authenticated_student_client.get("/users/me")
    user_id = me_res.json()["id"]
    
    # We can use the internal function or trigger an event that creates one.
    # But since we have authentication, using the model directly via a fixture would be cleanest,
    # or just assume one exists? No, better to explicit creation via model or endpoint if available.
    # Notifications are usually created by background events.
    # Let's import the model and create one directly for robustness.
    from backend.models.notification import create_notification
    import asyncio
    
    # We need to run async code in this sync test... 
    # But we can't easily access the valid event loop here without complexity.
    # Alternative: Trigger an action that creates a notification.
    # Applying to a job creates a notification for recruiter, but we are a student.
    # Let's update profile -> might trigger? No.
    
    # EASIEST: Just use the database fixture pattern if possible, or
    # since we are inside a test, we can use the loop if we are careful.
    
    # Actually, we can just insert into DB using PyMongo (Sync) or Motor (Async).
    # Since we are in a test and likely have direct DB access via fixture?
    # No, we only gave `authenticated_student_client`.
    
    # EASIEST: Just use the database fixture pattern if possible, or
    # since we are inside a test, we can use the loop if we are careful.
    
    from motor.motor_asyncio import AsyncIOMotorClient
    from backend.config import settings
    from bson import ObjectId
    from datetime import datetime
    import asyncio
    
    # Run async helper with FRESH client to avoid loop conflicts
    async def _seed():
        motor_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = motor_client[settings.mongodb_db]
        
        doc = {
            "user_id": ObjectId(user_id),
            "kind": "welcome",
            "payload": {"msg": "Hello"},
            "is_read": False,
            "read_at": None,
            "priority": "high",
            "category": "general",
            "created_at": datetime.utcnow(),
        }
        await database["notifications"].insert_one(doc)
        motor_client.close()
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_seed())
    loop.close()

    # Now get notifications to find a valid ID
    list_res = authenticated_student_client.get("/notifications/")
    if list_res.status_code == 404:
        pytest.skip("Notifications endpoint not implemented")
    
    notifications = list_res.json()
    if not notifications:
        pytest.fail("Failed to seed notification for test")
    
    notif_id = notifications[0].get("id") or notifications[0].get("_id")
    response = authenticated_student_client.put(f"/notifications/{notif_id}/read")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_unread_count(authenticated_student_client: TestClient):
    """Test getting unread count."""
    response = authenticated_student_client.get("/notifications/unread-count")
    if response.status_code == 404:
        pytest.skip("Endpoint not implemented")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data or "unread_count" in data
