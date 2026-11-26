from types import SimpleNamespace

import pytest

from backend import worker_health


class FakeRedis:
    def __init__(self, value=None):
        self.value = value
        self.sets = []

    async def get(self, key):
        return self.value

    async def set(self, key, value, ex=None):
        self.sets.append((key, value, ex))


class FakeOutbox:
    async def get_stats(self):
        return {"pending": 7, "processing": 1, "processed": 10, "failed": 0}


class FailingRedis:
    async def get(self, key):
        raise RuntimeError("secret://redis-host")


class FailingOutbox:
    async def get_stats(self):
        raise RuntimeError("secret://outbox-host")


@pytest.mark.asyncio
async def test_worker_health_reports_heartbeat_and_pending_outbox(monkeypatch):
    redis = FakeRedis("2026-11-26T00:00:00+00:00")
    monkeypatch.setattr(
        worker_health,
        "RedisClient",
        SimpleNamespace(get_instance=lambda: redis),
    )
    monkeypatch.setattr(worker_health, "outbox", FakeOutbox())

    result = await worker_health.get_worker_health()

    assert result == {
        "status": "ok",
        "pending_outbox": 7,
        "heartbeat": True,
    }


@pytest.mark.asyncio
async def test_worker_health_degrades_without_heartbeat(monkeypatch):
    monkeypatch.setattr(
        worker_health,
        "RedisClient",
        SimpleNamespace(get_instance=lambda: FakeRedis()),
    )
    monkeypatch.setattr(worker_health, "outbox", FakeOutbox())

    result = await worker_health.get_worker_health()

    assert result["status"] == "degraded"
    assert result["heartbeat"] is False


@pytest.mark.asyncio
async def test_worker_health_degrades_when_redis_fails(monkeypatch):
    monkeypatch.setattr(
        worker_health,
        "RedisClient",
        SimpleNamespace(get_instance=lambda: FailingRedis()),
    )
    monkeypatch.setattr(worker_health, "outbox", FakeOutbox())

    result = await worker_health.get_worker_health()

    assert result == {
        "status": "degraded",
        "pending_outbox": 0,
        "heartbeat": False,
    }


@pytest.mark.asyncio
async def test_worker_health_degrades_when_outbox_fails(monkeypatch):
    monkeypatch.setattr(
        worker_health,
        "RedisClient",
        SimpleNamespace(get_instance=lambda: FakeRedis("2026-11-26T00:00:00+00:00")),
    )
    monkeypatch.setattr(worker_health, "outbox", FailingOutbox())

    result = await worker_health.get_worker_health()

    assert result == {
        "status": "degraded",
        "pending_outbox": 0,
        "heartbeat": False,
    }


@pytest.mark.asyncio
async def test_record_worker_heartbeat_uses_short_ttl(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(
        worker_health,
        "RedisClient",
        SimpleNamespace(get_instance=lambda: redis),
    )

    await worker_health.record_worker_heartbeat()

    assert len(redis.sets) == 1
    assert redis.sets[0][0] == worker_health.WORKER_HEARTBEAT_KEY
    assert redis.sets[0][2] == 60
