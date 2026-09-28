"""
Auth blacklist fail-closed behavior tests.

Verifies that is_token_blacklisted raises TokenBlacklistUnavailableError when
Redis is unavailable, rather than silently returning False (fail-open).
"""

import pytest


def test_is_token_blacklisted_normal(client):
    """When Redis is available, a non-blacklisted JTI returns False."""
    import asyncio
    from backend.utils.auth import is_token_blacklisted

    async def _check():
        return await is_token_blacklisted("nonexistent-jti-123")

    result = asyncio.run(_check())
    assert result is False


def test_is_token_blacklisted_redis_unavailable(client, monkeypatch):
    """When Redis is down, is_token_blacklisted must NOT fail open."""
    import asyncio
    from backend.utils.auth import (
        is_token_blacklisted,
        TokenBlacklistUnavailableError,
    )

    def fake_get_redis():
        raise RuntimeError("Redis connection refused")

    # get_redis is imported from backend.redis_client inside the function
    import backend.redis_client as redis_mod
    monkeypatch.setattr(redis_mod, "get_redis", fake_get_redis)

    async def _check():
        return await is_token_blacklisted("jti-123")

    with pytest.raises(TokenBlacklistUnavailableError):
        asyncio.run(_check())


def test_current_user_fails_closed_on_redis_down(client, student_token, monkeypatch):
    """Authenticated request returns 503 (not 200) when Redis blacklist is down."""
    def fake_get_redis():
        raise RuntimeError("Redis unavailable")

    import backend.redis_client as redis_mod
    monkeypatch.setattr(redis_mod, "get_redis", fake_get_redis)

    # An authenticated endpoint should now fail-closed (503)
    resp = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 503
