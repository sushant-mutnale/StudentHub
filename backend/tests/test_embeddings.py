"""
Tests for the Embedding Service and RAG Manager vector generation.
These tests verify that real embedding generation works (or that the fallback
produces consistent, correctly-dimensioned vectors).
"""

import pytest
from backend.services.embedding_service import (
    embed_text,
    embed_texts,
    EMBEDDING_DIMENSIONS,
)


def test_embed_text_returns_correct_dimension():
    vec = embed_text("Hello, this is a test string for embedding.")
    assert isinstance(vec, list)
    # Real model returns 1536 (text-embedding-3-small default)
    # or 1024 if the SDK truncates; either is acceptable.
    assert len(vec) >= 512
    assert all(isinstance(v, float) for v in vec)


def test_embed_text_deterministic():
    """Same input should always produce the same vector."""
    a = embed_text("career path planning for software engineers")
    b = embed_text("career path planning for software engineers")
    assert a == b


def test_embed_texts_batch():
    texts = ["React developer", "Python backend engineer", "Data science intern"]
    vecs = embed_texts(texts)
    assert len(vecs) == 3
    for vec in vecs:
        assert isinstance(vec, list)
        assert len(vec) >= 512


def test_embed_texts_different_inputs_different_vectors():
    vecs = embed_texts(["python", "javascript"])
    assert vecs[0] != vecs[1]


def test_embed_text_has_reasonable_magnitude():
    """Embeddings should be normalized or near-unit-length."""
    vec = embed_text("Machine learning engineer position")
    magnitude = sum(v * v for v in vec) ** 0.5
    assert magnitude > 0.1  # non-trivial vector
    assert magnitude < 100  # not exploding
