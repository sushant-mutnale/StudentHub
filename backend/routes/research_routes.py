"""
Research Routes
API endpoints for deep research and company insights.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.research_agent import research_tool
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/research", tags=["research"])


# ============ Request/Response Models ============

class ResearchCompanyRequest(BaseModel):
    """Request for comprehensive company research."""
    company: str = Field(..., min_length=1, description="Company name to research")
    categories: List[str] = Field(
        default=["interview", "culture", "tech_stack"],
        description="Categories: interview, culture, salary, tech_stack, news"
    )
    max_results: int = Field(default=5, ge=1, le=10)


class InterviewQuestionsRequest(BaseModel):
    """Request for interview questions."""
    company: str = Field(..., min_length=1)
    role: str = Field(default="Software Engineer")


class CompanyTrendsRequest(BaseModel):
    """Request for company trends."""
    company: str = Field(..., min_length=1)


# ============ Research Endpoints ============

@router.post("/company")
async def research_company(
    payload: ResearchCompanyRequest,
    current_user=Depends(get_current_user)
):
    """
    Comprehensive company research for interview preparation.
    
    Gathers data on interview process, culture, salary, tech stack, and news.
    Uses SerpAPI for search and LLM for summarization.
    """
    try:
        results = await research_tool.research_company(
            company_name=payload.company,
            categories=payload.categories,
            max_results_per_category=payload.max_results
        )
        
        return {
            "status": "success",
            "research": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/interview-questions")
async def get_interview_questions(
    payload: InterviewQuestionsRequest,
    current_user=Depends(get_current_user)
):
    """
    Get common interview questions for a company/role.
    
    Extracts questions from research data and categorizes them.
    """
    try:
        results = await research_tool.get_interview_questions(
            company=payload.company,
            role=payload.role
        )
        
        return {
            "status": "success",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")


@router.post("/trends")
async def get_company_trends(
    payload: CompanyTrendsRequest,
    current_user=Depends(get_current_user)
):
    """
    Get latest trends and news about a company.
    
    Useful for staying updated before interviews.
    """
    try:
        results = await research_tool.get_company_trends(payload.company)
        
        return {
            "status": "success",
            "trends": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


# ============ Quick Research (Demo) ============

@router.get("/quick/{company}")
async def quick_research(company: str):
    """
    Quick company research (limited, no auth for demo).
    
    Returns basic interview and culture data.
    """
    try:
        results = await research_tool.research_company(
            company_name=company,
            categories=["interview"],
            max_results_per_category=3
        )
        
        return {
            "status": "success",
            "company": company,
            "summary": results.get("summary", ""),
            "insights": results.get("key_insights", []),
            "interview_data": results.get("categories", {}).get("interview", [])[:3]
        }
    except Exception as e:
        return {
            "status": "partial",
            "company": company,
            "error": str(e),
            "fallback_data": research_tool._get_mock_results(company, "interview")
        }


# ============ Cache Management ============

@router.post("/cache/clear")
async def clear_research_cache(current_user=Depends(get_current_user)):
    """Clear the research cache to force fresh data."""
    research_tool.clear_cache()
    return {"status": "success", "message": "Research cache cleared"}


# ============ Available Categories ============

@router.get("/categories")
async def get_research_categories():
    """Get list of available research categories."""
    return {
        "status": "success",
        "categories": [
            {
                "id": "interview",
                "name": "Interview Questions",
                "description": "Common interview questions and experiences"
            },
            {
                "id": "culture",
                "name": "Company Culture",
                "description": "Work culture, reviews, work-life balance"
            },
            {
                "id": "salary",
                "name": "Salary Data",
                "description": "Compensation packages and salary ranges"
            },
            {
                "id": "tech_stack",
                "name": "Technology Stack",
                "description": "Programming languages, frameworks, and tools"
            },
            {
                "id": "news",
                "name": "Latest News",
                "description": "Recent announcements, hiring updates"
            }
        ]
    }


# ============ Background Research Task ============

@router.post("/background/{company}")
async def start_background_research(
    company: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """
    Start comprehensive research in background.
    
    Useful for pre-fetching data before interviews.
    """
    async def do_research():
        await research_tool.research_company(
            company_name=company,
            categories=["interview", "culture", "salary", "tech_stack", "news"],
            max_results_per_category=5
        )
    
    background_tasks.add_task(do_research)
    
    return {
        "status": "started",
        "message": f"Background research started for {company}",
        "company": company
    }
