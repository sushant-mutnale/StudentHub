import asyncio

import pytest

from backend.interview_engine import worker


class _Engine:
    def __init__(self, result=0, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    async def drain_outbox(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


async def test_drain_once_delegates_to_the_engine():
    engine = _Engine(result=3)
    assert await worker.drain_once(engine=engine) == 3
    assert engine.calls == 1


async def test_outbox_loop_stops_on_the_stop_event():
    engine = _Engine()
    stop = asyncio.Event()
    stop.set()
    await worker.run_interview_engine_outbox(
        interval_seconds=0.01, stop_event=stop, engine=engine
    )
    assert engine.calls == 0


async def test_outbox_loop_survives_a_drain_failure():
    stop = asyncio.Event()

    class _FailingEngine:
        def __init__(self):
            self.calls = 0

        async def drain_outbox(self):
            self.calls += 1
            if self.calls >= 2:
                stop.set()
            raise RuntimeError("mongo exploded")

    engine = _FailingEngine()
    await worker.run_interview_engine_outbox(
        interval_seconds=0.001, stop_event=stop, engine=engine
    )
    assert engine.calls == 2
