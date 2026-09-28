"""
Tests for RAG recall evaluation metrics.
Uses synthetic retrieved results to validate precision, recall, and MRR
calculations without requiring Pinecone or OpenAI.
"""

import pytest
from backend.services.rag_eval import (
    evaluate_recall,
    EvalQuery,
    EvalSummary,
)


def _make_queries():
    return [
        EvalQuery(
            query="React developer",
            expected_doc_ids=["job_react_1", "job_react_2"],
        ),
        EvalQuery(
            query="Python data engineer",
            expected_doc_ids=["job_python_1"],
        ),
    ]


def test_perfect_recall():
    queries = _make_queries()
    retrieved = {
        "React developer": ["job_react_1", "job_react_2", "job_other"],
        "Python data engineer": ["job_python_1"],
    }
    summary = evaluate_recall(retrieved, queries, k=10)
    assert isinstance(summary, EvalSummary)
    assert summary.total_queries == 2
    assert summary.avg_recall_at_k == 1.0
    assert summary.avg_mrr == 1.0


def test_partial_recall():
    queries = _make_queries()
    retrieved = {
        "React developer": ["job_react_1", "job_unrelated"],
        "Python data engineer": ["unrelated"],
    }
    summary = evaluate_recall(retrieved, queries, k=10)
    assert 0.0 < summary.avg_recall_at_k < 1.0
    # React query: 1 of 2 expected found at pos 1 => recall=0.5, precision=1/10
    react_result = summary.per_query[0]
    assert react_result.recall_at_k == pytest.approx(0.5)
    assert react_result.precision_at_k == pytest.approx(0.1)
    # Python query: 0 of 1 expected
    py_result = summary.per_query[1]
    assert py_result.recall_at_k == pytest.approx(0.0)
    assert py_result.precision_at_k == pytest.approx(0.0)


def test_mrr():
    queries = [
        EvalQuery(query="test", expected_doc_ids=["target"]),
    ]
    # target is at position 3 => MRR = 1/3
    summary = evaluate_recall({"test": ["a", "b", "target"]}, queries, k=10)
    assert summary.avg_mrr == pytest.approx(1 / 3)


def test_no_results():
    summary = evaluate_recall({"q": []}, _make_queries(), k=10)
    assert summary.avg_recall_at_k == 0.0
    assert summary.avg_mrr == 0.0


def test_k_cuts_off_results():
    queries = [EvalQuery(query="q", expected_doc_ids=["hit"])]
    # hit is at position 5, but k=3
    summary = evaluate_recall({"q": ["a", "b", "c", "d", "hit"]}, queries, k=3)
    assert summary.avg_recall_at_k == 0.0
    assert summary.avg_mrr == 0.0
