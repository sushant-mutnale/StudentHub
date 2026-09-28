"""
Tests for RAG event handlers.
Verifies that RAG vectorization handlers are registered and fire correctly
on job-posted events without crashing (Pinecone may be unavailable in tests).
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.events.event_bus import event_bus, Event, EventTypes
from backend.events.handlers.rag_handler import register_rag_handlers, _vectorize_job


@pytest.fixture(autouse=True)
def _register():
    """Ensure RAG handlers are registered before each test."""
    register_rag_handlers()


def test_rag_handlers_registered():
    assert EventTypes.JOB_POSTED in event_bus._subscribers
    assert _vectorize_job in event_bus._subscribers[EventTypes.JOB_POSTED]


@pytest.mark.asyncio
async def test_vectorize_job_calls_rag_manager():
    """When rag_manager is available, the handler should upsert."""
    mock_rag = AsyncMock()
    with patch("backend.events.handlers.rag_handler.rag_manager", mock_rag, create=True):
        # The handler imports rag_manager at call time via lazy import;
        # patch it on the module so the import path resolves.
        import backend.services.rag_manager as rm
        original = rm.rag_manager
        rm.rag_manager = mock_rag
        try:
            event = Event(
                type=EventTypes.JOB_POSTED,
                payload={
                    "id": "test_job_123",
                    "title": "Backend Engineer",
                    "description": "Build scalable APIs",
                    "company_name": "Acme Corp",
                    "location": "Remote",
                },
            )
            await _vectorize_job(event)
            mock_rag.add_public_job.assert_called_once()
            args, kwargs = mock_rag.add_public_job.call_args
            assert kwargs.get("job_id") == "test_job_123"
            assert "Backend Engineer" in kwargs.get("job_text", "") or "Backend Engineer" in (args[1] if len(args) > 1 else "")
        finally:
            rm.rag_manager = original


@pytest.mark.asyncio
async def test_vectorize_job_missing_id_is_noop():
    event = Event(type=EventTypes.JOB_POSTED, payload={"title": "No ID"})
    # Should not raise
    await _vectorize_job(event)
