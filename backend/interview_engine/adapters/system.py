import uuid
from datetime import datetime
from typing import Dict, Tuple


class SystemClock:
    def now(self) -> datetime:
        return datetime.utcnow()


class UuidIds:
    def new_id(self) -> str:
        return str(uuid.uuid4())

    def new_token(self) -> str:
        return uuid.uuid4().hex


class InMemoryLease:
    def __init__(self):
        self._leases: Dict[str, Tuple[str, str]] = {}

    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        if session_id in self._leases:
            return False
        self._leases[session_id] = (device_id, token)
        return True

    async def current(self, session_id: str):
        return self._leases.get(session_id)

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        held = self._leases.get(session_id)
        return held == (device_id, token)

    async def takeover(
        self,
        session_id: str,
        device_id: str,
        token: str,
        ttl_seconds: int,
        expected_token: str,
    ) -> bool:
        held = self._leases.get(session_id)
        if held is not None and held[1] != expected_token:
            return False
        self._leases[session_id] = (device_id, token)
        return True

    async def release(self, session_id: str, token: str) -> None:
        held = self._leases.get(session_id)
        if held and held[1] == token:
            self._leases.pop(session_id, None)
