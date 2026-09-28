"""
Fit Scoring Service

Single source of truth for the "fit score" shared by both students and recruiters.

Both student job recommendations and recruiter candidate matching MUST go through
ScoringEngine.calculate_job_score() to guarantee score consistency.

This module provides a thin, convenient API on top of that engine for common use cases.
"""

import logging
from typing import Any, Dict, List, Optional

from .recommendation_engine import ScoringEngine, normalize_skill, normalize_skills

logger = logging.getLogger(__name__)


def calculate_fit_score(student: Dict, job: Dict) -> Dict[str, Any]:
    """
    Authoritative bidirectional fit score between a student and a job.

    Returns the same result regardless of who initiated the query
    (student looking at a job, or recruiter looking at a candidate).

    The returned dict contains:
      - total_score: float (0–100, 1 decimal)
      - breakdown: dict of per-component scores with weights and reasons
      - matched_skills: list of skill names the student has
      - missing_skills: list of skill names the student lacks
    """
    return ScoringEngine.calculate_job_score(student, job)


def rank_candidates_for_job(
    job: Dict,
    candidates: List[Dict],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Score and rank a list of student candidates against a job.

    Returns a list of dicts sorted descending by total_score, each containing:
      - student_id: str
      - score: float
      - explanation: dict (full breakdown + matched/missing skills)

    Does not enforce authorization — the caller must ensure the recruiter
    owns the job and the candidates are legitimate.
    """
    results: List[Dict[str, Any]] = []

    for student in candidates:
        try:
            fit = calculate_fit_score(student, job)
            results.append({
                "student_id": str(student.get("_id")),
                "score": fit["total_score"],
                "explanation": fit["breakdown"],
                "matched_skills": fit.get("matched_skills", []),
                "missing_skills": fit.get("missing_skills", []),
                "recommendation": fit.get("recommendation", ""),
            })
        except Exception as e:
            logger.warning("Failed to score student %s: %s", student.get("_id"), e)
            continue

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


async def retrieve_candidates_for_job(
    job: Dict,
    limit: int = 50,
) -> List[Dict]:
    """
    Retrieve candidates for a job using a layered approach:
      1. Semantic recall via RAG (vector search on job description)
      2. Fallback: regex skill matching via MongoDB

    Returns raw student docs — NOT yet scored.
    Scoring should be applied AFTER retrieval via rank_candidates_for_job.
    """
    required_skills = job.get("skills_required", [])
    job_description = job.get("description", "")
    candidates: List[Dict] = []

    # Layer 1: Semantic recall via Pinecone (fast, broad)
    try:
        from ..services.pinecone_service import get_index
        from ..models.user import users_collection
        from bson import ObjectId

        if job_description:
            search_res = await _search_pinecone_st(job_description, top_k=limit * 2)
            if search_res:
                ids = [
                    ObjectId(m["id"])
                    for m in search_res
                    if m.get("id") and ObjectId.is_valid(m["id"])
                ]
                if ids:
                    cursor = users_collection().find({
                        "role": "student",
                        "_id": {"$in": ids},
                    })
                    db_students = await cursor.to_list(length=len(ids))
                    # Preserve Pinecone rank order
                    id_map = {str(s["_id"]): s for s in db_students}
                    candidates = [id_map[str(oid)] for oid in ids if str(oid) in id_map]
                    if candidates:
                        logger.info("RAG recall: %d candidates for job %s", len(candidates), job.get("title"))
                        return candidates
    except Exception as e:
        logger.debug("Semantic candidate retrieval failed, using fallback: %s", e)

    # Layer 2: Skill regex fallback (deterministic, reliable)
    from ..models.user import users_collection
    try:
        query: Dict[str, Any] = {"role": "student"}
        if required_skills:
            # Use any one of the skills as the initial filter
            query["$or"] = [
                {"skills": {"$regex": skill, "$options": "i"}}
                for skill in required_skills[:5]
            ]
        cursor = users_collection().find(query).limit(limit * 2)
        candidates = await cursor.to_list(length=limit * 2)
    except Exception as e:
        logger.error("Fallback candidate retrieval failed: %s", e)
        candidates = []

    return candidates


async def _search_pinecone_st(query_text: str, top_k: int = 20) -> Optional[List[Dict]]:
    """Search Pinecone with the real query text and return match dicts."""
    try:
        from ..services.pinecone_service import get_index
        from ..services.embedding_service import embed_text
        idx = get_index()
        if not idx:
            return None
        vector = embed_text(query_text)
        res = idx.query(
            namespace="user_data",
            vector=vector,
            top_k=top_k,
            include_metadata=False,
        )
        return [{"id": m.id, "score": getattr(m, "score", 0)} for m in (res.matches or [])]
    except Exception:
        return None
