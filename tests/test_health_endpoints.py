from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class FakeDb:
    async def command(self, name):
        raise RuntimeError("secret://database-host")


def test_readiness_hides_error_details(monkeypatch):
    async def fake_ping():
        return True

    monkeypatch.setattr("backend.main.get_database", lambda: FakeDb())
    monkeypatch.setattr("backend.redis_client.RedisClient.ping", staticmethod(fake_ping))

    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["mongodb"] == "error"
    assert "secret://database-host" not in response.text


async def fake_worker_health():
    return {
        "status": "ok",
        "pending_outbox": 2,
        "heartbeat": True,
    }


def test_worker_health_endpoint_returns_state_only(monkeypatch):
    monkeypatch.setattr("backend.main.get_worker_health", fake_worker_health)

    response = client.get("/health/worker")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "pending_outbox": 2,
        "heartbeat": True,
    }


def test_worker_health_endpoint_degrades_without_error_detail(monkeypatch):
    async def failing_worker_health():
        raise RuntimeError("secret://outbox-host")

    monkeypatch.setattr("backend.main.get_worker_health", failing_worker_health)

    response = client.get("/health/worker")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "pending_outbox": 0,
        "heartbeat": False,
    }
    assert "secret://outbox-host" not in response.text
