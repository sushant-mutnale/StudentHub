"""
Embedding Service

Provides text embedding generation for RAG using OpenAI's text-embedding-3-small.
Falls back to a deterministic dummy vector for local/dev environments without an API key.
"""

import hashlib
import logging
from typing import List, Optional

from ..config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # model default; may differ at runtime
DUMMY_DIMENSIONS = 1024  # legacy dummy dimension for dev fallback


def _get_openai_client():
    """Lazily create an OpenAI client only if a key is configured."""
    api_key = settings.openai_api_key
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.warning("openai package not installed; using dummy embeddings")
        return None
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None


def _dummy_embedding(text: str, dim: int = DUMMY_DIMENSIONS) -> List[float]:
    """Generate a deterministic pseudo-embedding for dev/test environments."""
    h = hashlib.sha512(text.encode("utf-8")).digest()
    vec = []
    for i in range(dim):
        idx = i % len(h)
        vec.append((h[idx] / 255.0) * 2 - 1)  # normalize to [-1, 1]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


_client_cache = None


def embed_text(text: str) -> List[float]:
    """Generate an embedding for a single text string."""
    global _client_cache
    if _client_cache is None:
        _client_cache = _get_openai_client()
    if _client_cache is None:
        return _dummy_embedding(text)
    try:
        resp = _client_cache.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding request failed; falling back to dummy: {e}")
        return _dummy_embedding(text, EMBEDDING_DIMENSIONS)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts in a single request (batched)."""
    global _client_cache
    if _client_cache is None:
        _client_cache = _get_openai_client()
    if _client_cache is None:
        return [_dummy_embedding(t) for t in texts]
    try:
        resp = _client_cache.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        # Response data is in order of input
        return [item.embedding for item in resp.data]
    except Exception as e:
        logger.error(f"Batch embedding failed; falling back to dummy: {e}")
        return [_dummy_embedding(t, EMBEDDING_DIMENSIONS) for t in texts]
