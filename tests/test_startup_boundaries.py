import pytest

import backend.main as main_module


@pytest.mark.asyncio
async def test_web_startup_only_connects_to_mongo(monkeypatch):
    calls = []

    async def fake_connect():
        calls.append("connect")

    async def fake_close():
        calls.append("close")

    def forbidden(*args, **kwargs):
        calls.append("forbidden")
        raise AssertionError("web startup must not run init or worker side effects")

    monkeypatch.setattr(main_module, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(main_module, "close_mongo_connection", fake_close)
    monkeypatch.setattr(main_module, "ensure_database_indexes", forbidden)
    monkeypatch.setattr(main_module, "seed_default_users", forbidden)
    monkeypatch.setattr(main_module.worker_manager, "register", forbidden)
    monkeypatch.setattr(main_module.worker_manager, "start_all", forbidden)
    monkeypatch.setattr(main_module.worker_manager, "stop_all", forbidden)

    await main_module.startup_event()
    await main_module.shutdown_event()

    assert calls == ["connect", "close"]
