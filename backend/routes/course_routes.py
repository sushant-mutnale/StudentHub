"""
Course Search Routes
API endpoints for dynamic course search and recommendations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.course_search import course_search_service
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/courses", tags=["courses"])


# ============ Request/Response Schemas ============

class CourseSearchRequest(BaseModel):
    query: str
    max_per_provider: int = 3
    providers: Optional[List[str]] = None  # ["youtube", "udemy", "coursera", "edx"]


class CourseRecommendationRequest(BaseModel):
    skill: str
    current_skills: Optional[List[str]] = None
    experience_level: str = "beginner"  # beginner, intermediate, advanced
    max_results: int = 5


class CourseResult(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    source: str
    type: str
    provider: str
    rating: Optional[float] = None
    channel: Optional[str] = None
    instructor: Optional[str] = None


class SearchResponse(BaseModel):
    status: str = "success"
    query: str
    providers_used: List[str]
    total_results: int
    results: List[dict]


class RecommendationResponse(BaseModel):
    status: str = "success"
    query: str
    recommendations: List[dict]
    ai_powered: bool
    ai_reasoning: Optional[str] = None
    providers_used: List[str]
    total_found: Optional[int] = None
    message: Optional[str] = None


# ============ Endpoints ============

@router.get("/providers")
async def get_available_providers():
    """Get list of enabled course search providers."""
    enabled = course_search_service.get_enabled_providers()
    
    provider_info = {
        "youtube": {
            "name": "YouTube",
            "description": "Educational video tutorials",
            "requires": "YOUTUBE_API_KEY"
        },
        "udemy": {
            "name": "Udemy",
            "description": "Online courses marketplace",
            "requires": "APIFY_TOKEN"
        },
        "coursera": {
            "name": "Coursera",
            "description": "University-backed courses",
            "requires": "APIFY_TOKEN"
        },
        "edx": {
            "name": "EdX",
            "description": "MIT/Harvard online courses",
            "requires": "APIFY_TOKEN"
        },
        "local": {
            "name": "Local Library",
            "description": "Curated free resources",
            "requires": None
        }
    }
    
    return {
        "status": "success",
        "enabled_providers": enabled,
        "provider_details": {k: v for k, v in provider_info.items() if k in enabled}
    }


@router.post("/search", response_model=SearchResponse)
async def search_courses(
    payload: CourseSearchRequest,
    current_user=Depends(get_current_user)
):
    """
    Search for courses/tutorials across multiple providers.
    
    Returns raw search results from enabled providers.
    For AI-ranked recommendations, use /recommend endpoint.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = await course_search_service.search_all(
        query=payload.query,
        max_per_provider=payload.max_per_provider,
        providers=payload.providers
    )
    
    return SearchResponse(
        query=results.get("query", payload.query),
        providers_used=results.get("providers_used", []),
        total_results=results.get("total_results", 0),
        results=results.get("all_results", [])
    )


@router.post("/recommend", response_model=RecommendationResponse)
async def get_course_recommendations(
    payload: CourseRecommendationRequest,
    current_user=Depends(get_current_user)
):
    """
    Get AI-ranked course recommendations for a skill.
    
    Searches multiple providers, then uses LLM to rank results
    based on student context (current skills, experience level).
    Falls back to top results if LLM unavailable.
    """
    if not payload.skill.strip():
        raise HTTPException(status_code=400, detail="Skill cannot be empty")
    
    # Get student's skills from profile if not provided
    current_skills = payload.current_skills
    if not current_skills:
        user_skills = current_user.get("skills", [])
        current_skills = [
            s.get("name") if isinstance(s, dict) else str(s)
            for s in user_skills
            if s
        ]
    
    context = {
        "skills": current_skills,
        "experience_level": payload.experience_level,
        "goal": f"Learn {payload.skill}"
    }
    
    results = await course_search_service.search_with_llm_ranking(
        query=payload.skill,
        student_context=context,
        max_results=payload.max_results
    )
    
    return RecommendationResponse(
        query=payload.skill,
        recommendations=results.get("recommendations", []),
        ai_powered=results.get("ai_powered", False),
        ai_reasoning=results.get("ai_reasoning"),
        providers_used=results.get("providers_used", []),
        total_found=results.get("total_found"),
        message=results.get("message")
    )


@router.get("/search/{skill}")
async def quick_search(
    skill: str,
    max_results: int = 10,
    current_user=Depends(get_current_user)
):
    """
    Quick search for courses by skill name.
    Convenience endpoint that combines search and basic ranking.
    """
    results = await course_search_service.search_all(
        query=skill,
        max_per_provider=max_results // 3 + 1
    )
    
    # Simple sorting: prefer variety of sources
    all_results = results.get("all_results", [])
    
    # Group by source to ensure variety
    by_source = {}
    for r in all_results:
        source = r.get("source", "Unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(r)
    
    # Interleave from different sources
    varied_results = []
    while len(varied_results) < max_results and by_source:
        for source in list(by_source.keys()):
            if by_source[source]:
                varied_results.append(by_source[source].pop(0))
            else:
                del by_source[source]
            if len(varied_results) >= max_results:
                break
    
    return {
        "status": "success",
        "skill": skill,
        "courses": varied_results,
        "total_found": len(all_results),
        "providers_used": results.get("providers_used", [])
    }
