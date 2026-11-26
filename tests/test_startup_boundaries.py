from datetime import datetime, timedelta

import pytest

import backend.init_jobs as init_jobs
import backend.main as main_module
import backend.services.opportunity_ingestion as ingestion_module


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


@pytest.mark.asyncio
async def test_startup_ingestion_check_treats_naive_legacy_timestamp_as_utc(monkeypatch):
    class FakeIngestionLogCollection:
        async def find_one(self, sort):
            return {"timestamp": datetime.utcnow() - timedelta(hours=25)}

    ingested = []

    async def fake_ingest_all(use_mock):
        ingested.append(use_mock)

    monkeypatch.setattr(
        ingestion_module,
        "ingestion_log_collection",
        lambda: FakeIngestionLogCollection(),
    )
    monkeypatch.setattr(ingestion_module.opportunity_ingestion, "ingest_all", fake_ingest_all)

    await init_jobs.run_startup_ingestion_check()

    assert ingested == [False]


@pytest.mark.asyncio
async def test_run_init_job_closes_mongo_when_index_creation_fails(monkeypatch):
    calls = []

    async def fake_connect():
        calls.append("connect")

    async def fake_close():
        calls.append("close")

    async def failing_indexes():
        calls.append("indexes")
        raise RuntimeError("index failure")

    async def forbidden(*args, **kwargs):
        calls.append("forbidden")
        raise AssertionError("init must stop after index failure")

    monkeypatch.setattr(init_jobs, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(init_jobs, "close_mongo_connection", fake_close)
    monkeypatch.setattr(init_jobs, "ensure_database_indexes", failing_indexes)
    monkeypatch.setattr(init_jobs, "seed_default_users", forbidden)
    monkeypatch.setattr(init_jobs, "run_startup_ingestion_check", forbidden)

    with pytest.raises(RuntimeError, match="index failure"):
        await init_jobs.run_init_job()

    assert calls == ["connect", "indexes", "close"]
