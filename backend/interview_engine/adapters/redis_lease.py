import json

_KEY = "interview_engine:lease:{session_id}"

_RELEASE = """
local raw = redis.call('get', KEYS[1])
if not raw then
  return 0
end
local held = cjson.decode(raw)
if held['token'] == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLease:
    def __init__(self, redis_client, prefix: str = _KEY):
        self._redis = redis_client
        self._prefix = prefix

    def _key(self, session_id: str) -> str:
        return self._prefix.format(session_id=session_id)

    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        value = json.dumps({"device_id": device_id, "token": token})
        return bool(await self._redis.set(self._key(session_id), value, nx=True, ex=ttl_seconds))

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        raw = await self._redis.get(self._key(session_id))
        if not raw:
            return False
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            held = json.loads(raw)
        except (ValueError, TypeError):
            return False
        if not isinstance(held, dict):
            return False
        return held.get("device_id") == device_id and held.get("token") == token

    async def takeover(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        value = json.dumps({"device_id": device_id, "token": token})
        return bool(await self._redis.set(self._key(session_id), value, ex=ttl_seconds))

    async def release(self, session_id: str, token: str) -> None:
        await self._redis.eval(_RELEASE, 1, self._key(session_id), token)
