import asyncio
import logging

logger = logging.getLogger(__name__)


async def drain_once(engine=None) -> int:
    if engine is None:
        from .adapters.factory import build_engine

        engine = build_engine()
    return await engine.drain_outbox()


async def run_interview_engine_outbox(
    interval_seconds: float = 2.0, stop_event=None, engine=None
) -> None:
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            processed = await drain_once(engine=engine)
            if processed:
                logger.info("interview engine outbox processed %s events", processed)
        except Exception:
            logger.exception("interview engine outbox drain failed")
        await asyncio.sleep(interval_seconds)
