from .redis_lease import RedisLease
from .scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from .system import InMemoryLease, SystemClock, UuidIds


def build_engine(
    store=None,
    lease=None,
    redis_client=None,
    analyzer=None,
    generator=None,
    evaluator=None,
):
    from ..application.engine import InterviewEngine

    if store is None:
        from ...database import get_database
        from ...redis_client import get_redis

        from .mongo_store import MongoSessionStore

        database = get_database()
        redis_client = redis_client or get_redis()
        store = MongoSessionStore(database, database.client)
        lease = lease or RedisLease(redis_client)
    if lease is None:
        lease = InMemoryLease()
    return InterviewEngine(
        store=store,
        lease=lease,
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=analyzer or HeuristicAnalyzer(),
        generator=generator or ScriptedQuestionGenerator(),
        evaluator=evaluator or DeterministicEvaluator(),
    )
