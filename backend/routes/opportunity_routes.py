"""
Opportunity Routes
API endpoints for external opportunities (jobs, hackathons, content).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..services.opportunity_ingestion import opportunity_ingestion
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/opportunities", tags=["opportunities"])


# ============ Request/Response Models ============

class IngestionResponse(BaseModel):
    status: str
    source: str
    total_fetched: int = 0
    inserted: int = 0
    updated: int = 0
    timestamp: str


class StatsResponse(BaseModel):
    totals: dict
    last_ingestion: dict


# ============ Jobs Endpoints ============

@router.get("/jobs")
async def list_jobs(
    skills: Optional[str] = Query(None, description="Comma-separated skills to filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    work_mode: Optional[str] = Query(None, description="remote, onsite, hybrid"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """
    List available job/internship opportunities.
    Filter by skills, location, and work mode.
    """
    skills_list = [s.strip() for s in skills.split(",")] if skills else None
    
    jobs = await opportunity_ingestion.get_jobs(
        skills=skills_list,
        location=location,
        work_mode=work_mode,
        limit=limit,
        skip=skip
    )
    
    return {
        "status": "success",
        "count": len(jobs),
        "jobs": jobs
    }


@router.post("/ingest/jobs")
async def trigger_jobs_ingestion(
    use_mock: bool = Query(True, description="Use mock data for demo"),
    current_user=Depends(get_current_user)
):
    """
    Trigger job ingestion from external sources.
    Admin/demo endpoint.
    """
    result = await opportunity_ingestion.jobs_service.ingest_jobs(use_mock)
    return {
        "status": "success",
        "ingestion": result
    }


# ============ Hackathons Endpoints ============

@router.get("/hackathons")
async def list_hackathons(
    themes: Optional[str] = Query(None, description="Comma-separated themes to filter"),
    status: Optional[str] = Query(None, description="open, closed, upcoming"),
    eligibility: Optional[str] = Query(None, description="students, all, professionals"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """
    List available hackathon opportunities.
    Filter by themes, status, and eligibility.
    """
    themes_list = [t.strip() for t in themes.split(",")] if themes else None
    
    hackathons = await opportunity_ingestion.get_hackathons(
        theme_tags=themes_list,
        status=status,
        eligibility=eligibility,
        limit=limit,
        skip=skip
    )
    
    return {
        "status": "success",
        "count": len(hackathons),
        "hackathons": hackathons
    }


@router.post("/ingest/hackathons")
async def trigger_hackathons_ingestion(
    use_mock: bool = Query(True, description="Use mock data for demo"),
    current_user=Depends(get_current_user)
):
    """
    Trigger hackathon ingestion from external sources.
    Admin/demo endpoint.
    """
    result = await opportunity_ingestion.hackathons_service.ingest_hackathons(use_mock)
    return {
        "status": "success",
        "ingestion": result
    }


# ============ Content Endpoints ============

@router.get("/content")
async def list_content(
    topic: Optional[str] = Query(None, description="Topic filter: AI/ML, Skills, Hiring, etc."),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """
    List trending content/news articles.
    Filter by topic.
    """
    articles = await opportunity_ingestion.get_content(
        topic=topic,
        limit=limit,
        skip=skip
    )
    
    return {
        "status": "success",
        "count": len(articles),
        "articles": articles
    }


@router.post("/ingest/content")
async def trigger_content_ingestion(
    use_mock: bool = Query(True, description="Use mock data for demo"),
    current_user=Depends(get_current_user)
):
    """
    Trigger content ingestion from news sources.
    Admin/demo endpoint.
    """
    result = await opportunity_ingestion.content_service.ingest_content(use_mock)
    return {
        "status": "success",
        "ingestion": result
    }


# ============ Combined Endpoints ============

@router.post("/ingest/all")
async def trigger_all_ingestion(
    use_mock: bool = Query(True, description="Use mock data for demo"),
    current_user=Depends(get_current_user)
):
    """
    Trigger ingestion for all opportunity types.
    Admin/demo endpoint.
    """
    result = await opportunity_ingestion.ingest_all(use_mock)
    return result


@router.get("/stats")
async def get_ingestion_stats(
    current_user=Depends(get_current_user)
):
    """
    Get statistics about ingested opportunities.
    """
    stats = await opportunity_ingestion.get_stats()
    return {
        "status": "success",
        "stats": stats
    }


# ============ Demo Endpoints (No Auth) ============

@router.get("/demo/jobs")
async def demo_list_jobs(
    skills: Optional[str] = None,
    limit: int = 10
):
    """Demo: List jobs without authentication."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else None
    jobs = await opportunity_ingestion.get_jobs(skills=skills_list, limit=limit)
    return {"count": len(jobs), "jobs": jobs}


@router.get("/demo/hackathons")
async def demo_list_hackathons(
    themes: Optional[str] = None,
    limit: int = 10
):
    """Demo: List hackathons without authentication."""
    themes_list = [t.strip() for t in themes.split(",")] if themes else None
    hackathons = await opportunity_ingestion.get_hackathons(theme_tags=themes_list, limit=limit)
    return {"count": len(hackathons), "hackathons": hackathons}


@router.get("/demo/content")
async def demo_list_content(
    topic: Optional[str] = None,
    limit: int = 10
):
    """Demo: List content without authentication."""
    articles = await opportunity_ingestion.get_content(topic=topic, limit=limit)
    return {"count": len(articles), "articles": articles}


@router.post("/demo/ingest")
async def demo_trigger_ingestion():
    """Demo: Trigger all ingestion with mock data."""
    result = await opportunity_ingestion.ingest_all(use_mock=True)
    return result
