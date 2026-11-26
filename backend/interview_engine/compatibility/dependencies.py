from fastapi import Depends

from ..adapters.factory import build_engine

_ENGINE = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = build_engine()
    return _ENGINE


def engine_dependency(engine=Depends(get_engine)):
    return engine


def reset_engine():
    global _ENGINE
    _ENGINE = None
