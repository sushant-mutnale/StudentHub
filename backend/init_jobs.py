from .database import close_mongo_connection, connect_to_mongo
from .models.indexes import ensure_database_indexes
from .seed import seed_default_users
from .config import settings


async def run_startup_ingestion_check():
    from datetime import datetime, timedelta, timezone

    from .services.opportunity_ingestion import (
        ingestion_log_collection,
        opportunity_ingestion,
    )

    latest_log = await ingestion_log_collection().find_one(sort=[("timestamp", -1)])
    needs_ingestion = False

    if not latest_log:
        needs_ingestion = True
    else:
        last_run = latest_log.get("timestamp")
        if last_run and last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        if last_run and (datetime.now(timezone.utc) - last_run) > timedelta(hours=24):
            needs_ingestion = True

    if needs_ingestion:
        await opportunity_ingestion.ingest_all(use_mock=False)


async def run_init_job():
    await connect_to_mongo()

    try:
        try:
            await ensure_database_indexes()
        except Exception:
            raise

        if settings.app_env.lower() != "production":
            await seed_default_users()

        await run_startup_ingestion_check()
    finally:
        await close_mongo_connection()
