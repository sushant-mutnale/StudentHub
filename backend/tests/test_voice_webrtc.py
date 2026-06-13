import pytest
from fastapi.testclient import TestClient
from backend.main import app
from .conftest import auth_headers

@pytest.mark.asyncio
async def test_livekit_token_generation(client, student_user, student_token):
    resp = await client.post(
        "/api/voice/token",
        json={
            "room_name": "test-room",
            "identity": "test-student-123",
            "name": "Test Student"
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "token" in data
    assert "url" in data
    assert data["url"] == "http://localhost:7880"

def test_websocket_stream_endpoint():
    with TestClient(app) as client:
        with client.websocket_connect("/api/voice/stream/test-session-abc") as websocket:
            # Send text command
            websocket.send_text("ping")
            data = websocket.receive_json()
            assert data["status"] == "acknowledged"
            assert data["text_received"] == "ping"
            
            # Send raw bytes
            websocket.send_bytes(b"\x00\x01\x02\x03")
            data = websocket.receive_json()
            assert data["status"] == "processing"
            assert data["bytes_received"] == 4
