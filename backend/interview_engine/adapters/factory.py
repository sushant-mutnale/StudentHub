from .llm import build_llm_adapters
from .redis_lease import RedisLease
from .scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from .system import InMemoryLease, SystemClock, UuidIds

_llm_adapters_built = False
_llm_adapters = None


def _shared_llm_adapters(settings):
    global _llm_adapters_built, _llm_adapters
    if not _llm_adapters_built:
        _llm_adapters = build_llm_adapters(settings)
        _llm_adapters_built = True
    return _llm_adapters


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

    if analyzer is None or generator is None or evaluator is None:
        from ...config import settings

        llm = _shared_llm_adapters(settings)
        if llm is not None:
            analyzer = analyzer or llm.analyzer
            generator = generator or llm.generator
            evaluator = evaluator or llm.evaluator

    return InterviewEngine(
        store=store,
        lease=lease,
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=analyzer or HeuristicAnalyzer(),
        generator=generator or ScriptedQuestionGenerator(),
        evaluator=evaluator or DeterministicEvaluator(),
    )
