"""
Company Interview Routes
API endpoints for company interview knowledge lookup.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.company_research import company_researcher
from ..schemas.company_schema import (
    CompanyLookupResponse,
    CompanyListResponse,
    CompanyListItem,
    CompanySearchResponse,
    AddCompanyRequest,
    AddCompanyResponse,
    PrepTipsRequest,
    PrepTipsResponse,
    DSATopicsResponse,
    BehavioralThemesResponse,
)
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/company", tags=["company-interview-knowledge"])


# ============ Get Company Interview Pattern ============

@router.get("/{company_name}", response_model=CompanyLookupResponse)
async def get_company_interview_pattern(
    company_name: str,
    role: Optional[str] = Query(None, description="Specific role like SDE-2, L4"),
):
    """
    Get interview pattern for a company.
    
    Returns:
    - Interview rounds and structure
    - DSA topics commonly asked
    - Behavioral themes/values
    - Preparation tips
    - Example questions
    """
    summary = await company_researcher.get_interview_summary(company_name, role)
    
    return CompanyLookupResponse(
        company=summary["company"],
        role=summary.get("role", "Software Engineer"),
        difficulty=summary["difficulty"],
        difficulty_score=summary["difficulty_score"],
        total_rounds=summary["total_rounds"],
        total_interview_time_minutes=summary["total_interview_time_minutes"],
        rounds=summary["rounds"],
        dsa_topics=summary["dsa_topics"],
        behavioral_themes=summary["behavioral_themes"],
        system_design_topics=summary.get("system_design_topics", []),
        tips=summary["tips"],
        example_questions=summary.get("example_questions", []),
        recommended_prep_weeks=summary["recommended_prep_weeks"],
        data_source=summary["data_source"]
    )


# ============ List All Companies ============

@router.get("/", response_model=CompanyListResponse)
async def list_companies():
    """List all companies in the knowledge base."""
    companies = await company_researcher.list_all_companies()
    
    items = []
    for company in companies:
        pattern = await company_researcher.get_company_interview_pattern(company)
        items.append(CompanyListItem(
            company=company,
            difficulty=pattern.get("difficulty", "medium"),
            total_rounds=pattern.get("total_rounds", 3),
            source=pattern.get("source", "seed_data")
        ))
    
    return CompanyListResponse(
        companies=items,
        total=len(items)
    )


# ============ Search Companies ============

@router.get("/search/{query}", response_model=CompanySearchResponse)
async def search_companies(
    query: str,
    limit: int = Query(10, ge=1, le=50)
):
    """Search for companies by name."""
    results = await company_researcher.search_companies(query, limit)
    
    items = [CompanyListItem(**r) for r in results]
    
    return CompanySearchResponse(
        query=query,
        results=items,
        total=len(items)
    )


# ============ Get DSA Topics ============

@router.get("/{company_name}/dsa-topics", response_model=DSATopicsResponse)
async def get_dsa_topics(company_name: str):
    """Get DSA topics commonly asked at a company."""
    topics = await company_researcher.get_dsa_topics(company_name)
    
    return DSATopicsResponse(
        company=company_name,
        topics=topics
    )


# ============ Get Behavioral Themes ============

@router.get("/{company_name}/behavioral", response_model=BehavioralThemesResponse)
async def get_behavioral_themes(company_name: str):
    """Get behavioral themes/values for a company."""
    themes = await company_researcher.get_behavioral_themes(company_name)
    
    return BehavioralThemesResponse(
        company=company_name,
        themes=themes
    )


# ============ Get Personalized Prep Tips ============

@router.post("/prep-tips", response_model=PrepTipsResponse)
async def get_preparation_tips(
    payload: PrepTipsRequest,
    current_user=Depends(get_current_user)
):
    """
    Get personalized preparation tips based on student skills.
    Uses AI to generate tailored advice.
    """
    tips = await company_researcher.get_preparation_tips(
        payload.company,
        payload.role,
        payload.student_skills
    )
    
    dsa_topics = await company_researcher.get_dsa_topics(payload.company)
    behavioral = await company_researcher.get_behavioral_themes(payload.company)
    
    return PrepTipsResponse(
        company=payload.company,
        tips=tips,
        dsa_focus=dsa_topics[:5],
        behavioral_focus=behavioral[:5]
    )


# ============ Add Company Knowledge (Admin) ============

@router.post("/add", response_model=AddCompanyResponse)
async def add_company_knowledge(
    payload: AddCompanyRequest,
    current_user=Depends(get_current_user)
):
    """
    Add or update company interview knowledge.
    Useful for adding companies not in seed data.
    """
    # For now, allow any authenticated user to add
    # In production, add admin check
    
    company_data = payload.dict()
    result = await company_researcher.add_company_knowledge(company_data)
    
    action = "added" if result != "updated" else "updated"
    
    return AddCompanyResponse(
        company=payload.company,
        message=f"Company {payload.company} {action} successfully"
    )


# ============ Compare Companies ============

@router.get("/compare/{company1}/{company2}")
async def compare_companies(company1: str, company2: str):
    """Compare interview patterns between two companies."""
    pattern1 = await company_researcher.get_interview_summary(company1)
    pattern2 = await company_researcher.get_interview_summary(company2)
    
    # Find common and unique topics
    topics1 = set(pattern1.get("dsa_topics", []))
    topics2 = set(pattern2.get("dsa_topics", []))
    
    common_topics = list(topics1 & topics2)
    unique_to_1 = list(topics1 - topics2)
    unique_to_2 = list(topics2 - topics1)
    
    return {
        "status": "success",
        "comparison": {
            "companies": [company1, company2],
            "difficulty": {
                company1: pattern1["difficulty"],
                company2: pattern2["difficulty"]
            },
            "total_rounds": {
                company1: pattern1["total_rounds"],
                company2: pattern2["total_rounds"]
            },
            "prep_weeks": {
                company1: pattern1["recommended_prep_weeks"],
                company2: pattern2["recommended_prep_weeks"]
            },
            "common_dsa_topics": common_topics,
            f"unique_to_{company1}": unique_to_1,
            f"unique_to_{company2}": unique_to_2,
        }
    }


# ============ Quick Lookup (No Auth) ============

@router.get("/quick/{company_name}")
async def quick_company_lookup(company_name: str):
    """
    Quick company lookup without authentication.
    Returns basic info only.
    """
    pattern = await company_researcher.get_company_interview_pattern(company_name)
    
    return {
        "status": "success",
        "company": pattern.get("company", company_name),
        "difficulty": pattern.get("difficulty", "medium"),
        "total_rounds": pattern.get("total_rounds", 3),
        "dsa_topics": pattern.get("dsa_topics", [])[:5],
        "tips": pattern.get("tips", [])[:3],
        "source": pattern.get("source", "unknown")
    }
