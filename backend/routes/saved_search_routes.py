"""
Saved Searches Routes

Endpoints for recruiters to save candidate search criteria and receive alerts
when new matching students join the platform.
"""

from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..models import saved_search as saved_search_model
from ..utils.dependencies import get_current_recruiter

router = APIRouter(prefix="/recruiter/saved-searches", tags=["saved-searches"])


class SavedSearchCreate(BaseModel):
    name: str = Field(..., max_length=100)
    skill: Optional[str] = None
    location: Optional[str] = None
    college: Optional[str] = None
    min_score: Optional[float] = None
    alert_enabled: bool = True


class SavedSearchResponse(BaseModel):
    id: str
    recruiter_id: str
    name: str
    filters: dict
    alert_enabled: bool
    last_checked_at: Optional[str] = None
    last_match_count: int = 0
    created_at: str
    updated_at: str


def _serialize(doc: dict) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=str(doc["_id"]),
        recruiter_id=str(doc["recruiter_id"]),
        name=doc.get("name") or "Untitled",
        filters=doc.get("filters") or {},
        alert_enabled=doc.get("alert_enabled", True),
        last_checked_at=doc.get("last_checked_at").isoformat() if doc.get("last_checked_at") else None,
        last_match_count=doc.get("last_match_count", 0),
        created_at=doc["created_at"].isoformat() if doc.get("created_at") else "",
        updated_at=doc["updated_at"].isoformat() if doc.get("updated_at") else "",
    )


@router.get("", response_model=List[SavedSearchResponse])
async def list_saved_searches(recruiter=Depends(get_current_recruiter)):
    """List all saved candidate searches for the recruiter."""
    searches = await saved_search_model.list_saved_searches(str(recruiter["_id"]))
    return [_serialize(s) for s in searches]


@router.post("", response_model=SavedSearchResponse, status_code=201)
async def create_saved_search(
    payload: SavedSearchCreate,
    recruiter=Depends(get_current_recruiter),
):
    """Create a new saved search."""
    doc = await saved_search_model.create_saved_search(
        str(recruiter["_id"]), payload.dict()
    )
    return _serialize(doc)


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: str,
    recruiter=Depends(get_current_recruiter),
):
    doc = await saved_search_model.get_saved_search(
        search_id, str(recruiter["_id"])
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return _serialize(doc)


@router.delete("/{search_id}", status_code=204)
async def delete_saved_search(
    search_id: str,
    recruiter=Depends(get_current_recruiter),
):
    deleted = await saved_search_model.delete_saved_search(
        search_id, str(recruiter["_id"])
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return None


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    skill: Optional[str] = None
    location: Optional[str] = None
    college: Optional[str] = None
    min_score: Optional[float] = None
    alert_enabled: Optional[bool] = None


class SavedSearchCandidate(BaseModel):
    id: str
    name: str
    skills: List[str] = []
    location: Optional[str] = None
    college: Optional[str] = None
    experience_years: Optional[float] = None


@router.patch("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: str,
    payload: SavedSearchUpdate,
    recruiter=Depends(get_current_recruiter),
):
    update_dict = {k: v for k, v in payload.dict().items() if v is not None}
    doc = await saved_search_model.update_saved_search(
        search_id, str(recruiter["_id"]), update_dict
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return _serialize(doc)


@router.get("/{search_id}/candidates", response_model=List[SavedSearchCandidate])
async def get_saved_search_candidates(
    search_id: str,
    limit: int = Query(20, ge=1, le=50),
    recruiter=Depends(get_current_recruiter),
):
    students = await saved_search_model.get_candidates_for_search(
        search_id, str(recruiter["_id"]), limit=limit
    )
    return [
        SavedSearchCandidate(
            id=str(s["_id"]),
            name=s.get("name") or "Anonymous",
            skills=s.get("skills") or [],
            location=s.get("location"),
            college=s.get("college"),
            experience_years=s.get("experience_years"),
        )
        for s in students
    ]
