"""
RAG Recall Evaluation

Provides precision/recall/MRR evaluation for the RAG search pipeline.
Compares actual search results against a gold-standard set of expected
relevant document IDs for a set of test queries.

The evaluation can be run:
- As a unit test (test_rag_eval.py) against mocked index results
- Via an API endpoint (admin-only) for live evaluation against Pinecone
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EvalQuery:
    query: str
    expected_doc_ids: List[str]
    description: Optional[str] = None


@dataclass
class EvalResult:
    query: str
    retrieved_ids: List[str]
    hits: List[str]
    precision_at_k: float
    recall_at_k: float
    mrr: float


@dataclass
class EvalSummary:
    total_queries: int
    avg_precision_at_k: float
    avg_recall_at_k: float
    avg_mrr: float
    per_query: List[EvalResult] = field(default_factory=list)


# ------------------------------------------------------------------
# Gold-standard evaluation queries
# ------------------------------------------------------------------

DEFAULT_EVAL_QUERIES = [
    EvalQuery(
        query="React developer position in Mumbai",
        expected_doc_ids=["job_react_mumbai", "job_frontend_mumbai"],
        description="Should find React jobs in Mumbai",
    ),
    EvalQuery(
        query="Python machine learning internship",
        expected_doc_ids=["job_ml_python", "job_data_science"],
        description="Should find ML/Python internships",
    ),
    EvalQuery(
        query="Software engineer remote job",
        expected_doc_ids=["job_swe_remote", "job_backend_remote"],
        description="Should find remote SWE positions",
    ),
    EvalQuery(
        query="Full stack developer with Node.js",
        expected_doc_ids=["job_fullstack_node"],
        description="Should find full-stack jobs mentioning Node",
    ),
    EvalQuery(
        query="Data analyst with SQL skills",
        expected_doc_ids=["job_data_analyst", "job_analytics_sql"],
        description="Should find data analyst positions",
    ),
]


# ------------------------------------------------------------------
# Metric computation helpers
# ------------------------------------------------------------------

def _precision_at_k(retrieved: List[str], expected: set, k: int) -> float:
    if k == 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in expected)
    return hits / k


def _recall_at_k(retrieved: List[str], expected: set, k: int) -> float:
    if not expected:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in expected)
    return hits / len(expected)


def _mrr(retrieved: List[str], expected: set, k: int) -> float:
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in expected:
            return 1.0 / (i + 1)
    return 0.0


# ------------------------------------------------------------------
# Core evaluation runner
# ------------------------------------------------------------------

def evaluate_recall(
    retrieved_results: Dict[str, List[str]],
    eval_queries: Optional[List[EvalQuery]] = None,
    k: int = 10,
) -> EvalSummary:
    """
    Evaluate recall against gold-standard expected document IDs.

    Args:
        retrieved_results: mapping of query -> list of retrieved doc IDs
        eval_queries: list of EvalQuery definitions
        k: cutoff for precision/recall@k
    """
    if eval_queries is None:
        eval_queries = DEFAULT_EVAL_QUERIES

    results: List[EvalResult] = []

    for eq in eval_queries:
        retrieved = retrieved_results.get(eq.query, [])
        expected = set(eq.expected_doc_ids)

        p = _precision_at_k(retrieved, expected, k)
        r = _recall_at_k(retrieved, expected, k)
        m = _mrr(retrieved, expected, k)
        hits = [doc_id for doc_id in retrieved[:k] if doc_id in expected]

        results.append(EvalResult(
            query=eq.query,
            retrieved_ids=retrieved[:k],
            hits=hits,
            precision_at_k=p,
            recall_at_k=r,
            mrr=m,
        ))

    n = len(results) or 1
    return EvalSummary(
        total_queries=len(results),
        avg_precision_at_k=sum(r.precision_at_k for r in results) / n,
        avg_recall_at_k=sum(r.recall_at_k for r in results) / n,
        avg_mrr=sum(r.mrr for r in results) / n,
        per_query=results,
    )


def evaluate_recall_from_index(
    index,
    eval_queries: Optional[List[EvalQuery]] = None,
    k: int = 10,
    namespace: str = "",
) -> EvalSummary:
    """Run live evaluation queries against a Pinecone index."""
    if eval_queries is None:
        eval_queries = DEFAULT_EVAL_QUERIES

    from .embedding_service import embed_text

    retrieved_map: Dict[str, List[str]] = {}

    for eq in eval_queries:
        try:
            vector = embed_text(eq.query)
            res = index.query(
                namespace=namespace,
                vector=vector,
                top_k=k,
                include_metadata=True,
            )
            retrieved_map[eq.query] = [m.id for m in res.matches]
        except Exception as e:
            logger.error(f"Evaluation query failed: {eq.query}: {e}")
            retrieved_map[eq.query] = []

    return evaluate_recall(retrieved_map, eval_queries, k)
