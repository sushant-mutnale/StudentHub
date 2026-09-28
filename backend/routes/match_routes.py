"""
Match Routes — Recruiter candidate matching using the SHARED fit-scoring engine.

All candidate scoring goes through `fit_scoring.calculate_fit_score` which wraps
`ScoringEngine.calculate_job_score` — the SAME engine used for student job
recommendations. This guarantees score consistency across both sides.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..models import job as job_model
from ..models import user as user_model
from ..schemas.user_schema import UserPublic, MatchResult, MatchExplanation
from ..utils.dependencies import get_current_recruiter
from ..services.fit_scoring import (
    calculate_fit_score,
    rank_candidates_for_job,
    retrieve_candidates_for_job,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Schema for the new ranked-candidates response
# ------------------------------------------------------------------

class RankedCandidate(BaseModel):
    student_id: str
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    explanation: dict = Field(default_factory=dict)
    student: UserPublic | None = None


class RankedCandidatesResponse(BaseModel):
    job_id: str
    job_title: str
    total_candidates: int
    candidates: List[RankedCandidate]


# ------------------------------------------------------------------
# Helper: build the full explanation from authoritative scoring
# ------------------------------------------------------------------

def _build_match_explanation(student: dict, job: dict) -> MatchExplanation:
    """Build MatchExplanation using the authoritative ScoringEngine."""
    fit = calculate_fit_score(student, job)
    breakdown = fit.get("breakdown", {})

    # Map authoritative component names into the legacy schema fields
    # so that existing frontend code continues to work.
    skill_data = breakdown.get("skill_match", {})
    prof_data  = breakdown.get("proficiency_fit", {})
    activity   = breakdown.get("ai_readiness", {})
    completeness = breakdown.get("career_alignment", {})

    return MatchExplanation(
        matched_skills=fit.get("matched_skills", []),
        missing_skills=fit.get("missing_skills", []),
        skill_match_score=skill_data.get("score", 0),
        proficiency_score=prof_data.get("score", 0),
        activity_score=activity.get("score", 0),
        completeness_score=completeness.get("score", 0),
        total_score=fit["total_score"],
        # Full authoritative breakdown (6 components)
        skill_match=skill_data.get("score"),
        proficiency_fit=prof_data.get("score"),
        freshness=breakdown.get("freshness", {}).get("score"),
        location_match=breakdown.get("location_match", {}).get("score"),
        career_alignment=breakdown.get("career_alignment", {}).get("score"),
        ai_readiness=activity.get("score"),
    )


def _student_to_match_result(student: dict, job: dict) -> MatchResult:
    """Convert a student document + job to a MatchResult using the authoritative scorer."""
    explanation = _build_match_explanation(student, job)
    return MatchResult(
        id=str(student.get("_id") or student.get("id")),
        role=student.get("role", "student"),
        username=student.get("username", ""),
        email=student.get("email", ""),
        full_name=student.get("full_name"),
        prn=student.get("prn"),
        college=student.get("college"),
        branch=student.get("branch"),
        year=student.get("year"),
        company_name=student.get("company_name"),
        contact_number=student.get("contact_number"),
        website=student.get("website"),
        company_description=student.get("company_description"),
        avatar_url=student.get("avatar_url"),
        bio=student.get("bio"),
        skills=student.get("skills") or [],
        ai_profile=student.get("ai_profile"),
        connections=student.get("connections") or [],
        created_at=student.get("created_at"),
        updated_at=student.get("updated_at"),
        match_score=explanation.total_score,
        explanation=explanation,
    )


# ------------------------------------------------------------------
# Existing endpoint: per-job matches (now uses authoritative scorer)
# ------------------------------------------------------------------

@router.get("/{job_id}/matches", response_model=List[MatchResult])
async def job_matches(job_id: str, recruiter=Depends(get_current_recruiter)):
    """Rank candidates for a job using the authoritative fit-scoring engine.

    Retrieval: RAG semantic recall with skill-regex fallback.
    Scoring: ScoringEngine.calculate_job_score (6-component, deterministic).
    Authorization: recruiter must own the job.
    """
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = await retrieve_candidates_for_job(job, limit=100)
    results = [_student_to_match_result(c, job) for c in candidates]
    results.sort(key=lambda r: r.match_score, reverse=True)
    return results


# ------------------------------------------------------------------
# New endpoint: structured ranked candidates for the recruiter UI
# ------------------------------------------------------------------

@router.get(
    "/{job_id}/ranked-candidates",
    response_model=RankedCandidatesResponse,
    tags=["recruiter"],
)
async def ranked_candidates(
    job_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    recruiter=Depends(get_current_recruiter),
):
    """Structured ranked candidate list for a job.

    Returns the authoritative fit score per candidate, with a full
    component breakdown and full student profile — everything a recruiter
    needs to make a screening decision in one call.

    Authorization: recruiter must own the job.
    """
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = await retrieve_candidates_for_job(job, limit=limit)
    ranked = rank_candidates_for_job(job, candidates, limit=limit)

    enriched: List[RankedCandidate] = []
    student_cache = {str(c.get("_id")): c for c in candidates}

    for r in ranked:
        sid = r["student_id"]
        student_doc = student_cache.get(sid)
        student_pub = None
        if student_doc:
            student_pub = UserPublic(
                id=sid,
                role=student_doc.get("role", "student"),
                username=student_doc.get("username", ""),
                email=student_doc.get("email", ""),
                full_name=student_doc.get("full_name"),
                prn=student_doc.get("prn"),
                college=student_doc.get("college"),
                branch=student_doc.get("branch"),
                year=student_doc.get("year"),
                avatar_url=student_doc.get("avatar_url"),
                bio=student_doc.get("bio"),
                skills=student_doc.get("skills") or [],
                ai_profile=student_doc.get("ai_profile"),
                connections=student_doc.get("connections") or [],
                created_at=student_doc.get("created_at"),
                updated_at=student_doc.get("updated_at"),
            )
        enriched.append(RankedCandidate(
            student_id=sid,
            score=r["score"],
            matched_skills=r["matched_skills"],
            missing_skills=r["missing_skills"],
            explanation=r["explanation"],
            student=student_pub,
        ))

    return RankedCandidatesResponse(
        job_id=job_id,
        job_title=job.get("title", ""),
        total_candidates=len(enriched),
        candidates=enriched,
    )
