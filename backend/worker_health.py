from datetime import datetime, timezone

from .models.outbox import outbox
from .redis_client import RedisClient

WORKER_HEARTBEAT_KEY = "studenthub:worker:heartbeat"
DEGRADED_WORKER_HEALTH = {
    "status": "degraded",
    "pending_outbox": 0,
    "heartbeat": False,
}


async def record_worker_heartbeat():
    client = RedisClient.get_instance()
    value = datetime.now(timezone.utc).isoformat()
    await client.set(WORKER_HEARTBEAT_KEY, value, ex=60)


async def get_worker_health():
    try:
        client = RedisClient.get_instance()
        heartbeat = await client.get(WORKER_HEARTBEAT_KEY)
        stats = await outbox.get_stats()
    except Exception:
        return dict(DEGRADED_WORKER_HEALTH)
    return {
        "status": "ok" if heartbeat else "degraded",
        "pending_outbox": stats["pending"],
        "heartbeat": bool(heartbeat),
    }
