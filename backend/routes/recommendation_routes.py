"""
Recommendation Routes
API endpoints for personalized opportunity recommendations.
Module 4 Week 2: Recommendation Engine APIs.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from bson import ObjectId

from ..services.recommendation_engine import recommendation_engine
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ============ Request/Response Models ============

class FeedbackRequest(BaseModel):
    opportunity_id: str
    opportunity_type: str = Field(..., description="job, hackathon, or content")
    action: str = Field(..., description="clicked, saved, applied, ignored, dismissed")
    recommendation_score: Optional[float] = None
    recommendation_rank: Optional[int] = None


class JobFilters(BaseModel):
    location: Optional[str] = None
    work_mode: Optional[str] = None
    min_stipend: Optional[int] = None


# ============ Job Recommendations ============

@router.get("/jobs")
async def get_job_recommendations(
    limit: int = Query(20, ge=1, le=50, description="Number of recommendations"),
    location: Optional[str] = Query(None, description="Filter by location"),
    work_mode: Optional[str] = Query(None, description="Filter: remote, onsite, hybrid"),
    current_user=Depends(get_current_user)
):
    """
    Get personalized job/internship recommendations.
    
    Scoring formula:
    - 40% Skill Match
    - 20% Proficiency Fit
    - 15% Freshness
    - 10% Location Match
    - 10% Career Alignment
    - 5% AI Profile Readiness
    
    Returns ranked jobs with match explanations.
    """
    student_id = str(current_user["_id"])
    
    filters = {}
    if location:
        filters["location"] = location
    if work_mode:
        filters["work_mode"] = work_mode
    
    result = await recommendation_engine.recommend_jobs(
        student_id=student_id,
        limit=limit,
        filters=filters if filters else None
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/hackathons")
async def get_hackathon_recommendations(
    limit: int = Query(10, ge=1, le=30, description="Number of recommendations"),
    theme: Optional[str] = Query(None, description="Filter by theme: AI, Web3, etc."),
    eligibility: Optional[str] = Query(None, description="Filter: students, all"),
    current_user=Depends(get_current_user)
):
    """
    Get personalized hackathon recommendations.
    
    Scoring formula:
    - 50% Theme/Tech Match
    - 25% Urgency (time to deadline)
    - 25% Difficulty Fit
    """
    student_id = str(current_user["_id"])
    
    filters = {}
    if theme:
        filters["theme"] = theme
    if eligibility:
        filters["eligibility"] = eligibility
    
    result = await recommendation_engine.recommend_hackathons(
        student_id=student_id,
        limit=limit,
        filters=filters if filters else None
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/content")
async def get_content_recommendations(
    limit: int = Query(15, ge=1, le=50, description="Number of recommendations"),
    topic: Optional[str] = Query(None, description="Filter by topic: AI, Skills, etc."),
    current_user=Depends(get_current_user)
):
    """
    Get personalized content/news recommendations.
    
    Scoring formula:
    - 60% Topic Relevance
    - 40% Recency
    """
    student_id = str(current_user["_id"])
    
    filters = {}
    if topic:
        filters["topic"] = topic
    
    result = await recommendation_engine.recommend_content(
        student_id=student_id,
        limit=limit,
        filters=filters if filters else None
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# ============ Combined Feed ============

@router.get("/feed")
async def get_recommendation_feed(
    jobs_limit: int = Query(5, ge=1, le=10),
    hackathons_limit: int = Query(3, ge=1, le=5),
    content_limit: int = Query(5, ge=1, le=10),
    current_user=Depends(get_current_user)
):
    """
    Get a combined feed of all recommendation types.
    Perfect for home page/dashboard display.
    """
    student_id = str(current_user["_id"])
    
    jobs_result = await recommendation_engine.recommend_jobs(student_id, jobs_limit)
    hackathons_result = await recommendation_engine.recommend_hackathons(student_id, hackathons_limit)
    content_result = await recommendation_engine.recommend_content(student_id, content_limit)
    
    return {
        "status": "success",
        "student_id": student_id,
        "feed": {
            "jobs": jobs_result.get("recommendations", []),
            "hackathons": hackathons_result.get("recommendations", []),
            "content": content_result.get("recommendations", [])
        },
        "totals": {
            "jobs_available": jobs_result.get("total_available", 0),
            "hackathons_available": hackathons_result.get("total_available", 0),
            "content_available": content_result.get("total_available", 0)
        }
    }


# ============ Feedback Tracking ============

@router.post("/feedback")
async def record_recommendation_feedback(
    feedback: FeedbackRequest,
    current_user=Depends(get_current_user)
):
    """
    Record user interaction with a recommendation.
    Used to improve future recommendations via feedback loop.
    
    Actions:
    - clicked: User clicked to view details
    - saved: User saved for later
    - applied: User applied/registered
    - ignored: User scrolled past (implicit)
    - dismissed: User explicitly dismissed
    """
    student_id = str(current_user["_id"])
    
    valid_types = {"job", "hackathon", "content"}
    valid_actions = {"clicked", "saved", "applied", "ignored", "dismissed"}
    
    if feedback.opportunity_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid opportunity_type. Must be one of: {valid_types}"
        )
    
    if feedback.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )
    
    result = await recommendation_engine.record_feedback(
        student_id=student_id,
        opportunity_id=feedback.opportunity_id,
        opportunity_type=feedback.opportunity_type,
        action=feedback.action,
        recommendation_score=feedback.recommendation_score,
        recommendation_rank=feedback.recommendation_rank
    )
    
    return result


@router.get("/stats")
async def get_recommendation_stats(
    current_user=Depends(get_current_user)
):
    """
    Get recommendation statistics for the current user.
    Shows engagement breakdown and improvement areas.
    """
    student_id = str(current_user["_id"])
    
    stats = await recommendation_engine.get_recommendation_stats(student_id)
    
    return {
        "status": "success",
        "student_id": student_id,
        "stats": stats
    }


# ============ Demo Endpoints (No Auth) ============

@router.get("/demo/jobs")
async def demo_job_recommendations(limit: int = 5):
    """
    Demo: Get job recommendations without authentication.
    Uses a sample student profile.
    """
    # Create mock student for demo
    mock_student = {
        "_id": "demo_student",
        "skills": [
            {"name": "python", "level": 70},
            {"name": "javascript", "level": 60},
            {"name": "react", "level": 55},
            {"name": "mongodb", "level": 50}
        ],
        "location": "Bangalore",
        "interests": ["AI", "backend development"],
        "ai_profile": {
            "overall_score": 65,
            "skill_score": 70,
            "interview_score": 60,
            "learning_score": 55
        },
        "learning_paths": [
            {"skill": "docker", "gap_priority": "HIGH"},
            {"skill": "aws", "gap_priority": "MEDIUM"}
        ]
    }
    
    from ..services.opportunity_ingestion import opportunity_ingestion
    
    # Get jobs
    jobs = await opportunity_ingestion.get_jobs(limit=50)
    
    # Score and rank
    from ..services.recommendation_engine import ScoringEngine
    scoring = ScoringEngine()
    
    scored = []
    for job in jobs:
        score_result = scoring.calculate_job_score(mock_student, job)
        scored.append({
            "job": job,
            "score": score_result["total_score"],
            "match_details": score_result["breakdown"],
            "recommendation": score_result["recommendation"]
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "status": "demo",
        "demo_student_profile": {
            "skills": [s["name"] for s in mock_student["skills"]],
            "location": mock_student["location"],
            "ai_score": mock_student["ai_profile"]["overall_score"]
        },
        "recommendations": scored[:limit]
    }


@router.get("/demo/explain/{job_id}")
async def demo_explain_match(job_id: str):
    """
    Demo: Get detailed match explanation for a specific job.
    """
    from ..services.opportunity_ingestion import opportunities_jobs_collection
    from ..services.recommendation_engine import ScoringEngine
    
    job = await opportunities_jobs_collection().find_one({"source_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    mock_student = {
        "skills": [
            {"name": "python", "level": 70},
            {"name": "javascript", "level": 60},
            {"name": "react", "level": 55}
        ],
        "location": "Bangalore",
        "interests": ["backend development"],
        "ai_profile": {"overall_score": 65, "interview_score": 60, "learning_score": 55},
        "learning_paths": [{"skill": "docker", "gap_priority": "HIGH"}]
    }
    
    scoring = ScoringEngine()
    score_result = scoring.calculate_job_score(mock_student, job)
    
    job["_id"] = str(job["_id"])
    
    return {
        "job": job,
        "total_score": score_result["total_score"],
        "detailed_breakdown": score_result["breakdown"],
        "recommendation": score_result["recommendation"]
    }
