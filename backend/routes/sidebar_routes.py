"""
Sidebar Routes
Provides dynamic data for the Right Sidebar: Upcoming Events and Recommended Resources.
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from datetime import datetime
from bson import ObjectId

from ..database import get_database
from ..utils.dependencies import get_current_user

router = APIRouter(tags=["sidebar"])

def opportunities_hackathons_collection():
    return get_database()["opportunities_hackathons"]

def opportunities_content_collection():
    return get_database()["opportunities_content"]

@router.get("/events/upcoming")
async def get_upcoming_events(
    limit: int = Query(3, ge=1, le=10),
    current_user=Depends(get_current_user)
):
    """
    Get upcoming events for the sidebar.
    Returns title, category, date & time, platform, registration URL, status.
    """
    now = datetime.utcnow()
    cursor = opportunities_hackathons_collection().find(
        {
            "status": {"$in": ["open", "upcoming", "live"]},
            "start_date": {"$gte": now}
        }
    ).sort("start_date", 1).limit(limit)
    
    events = await cursor.to_list(length=limit)
    
    results = []
    for e in events:
        results.append({
            "id": str(e["_id"]),
            "title": e.get("event_name"),
            "category": "Hackathon" if not e.get("theme_tags") else e.get("theme_tags")[0],
            "date": e.get("start_date"),
            "platform": e.get("organizer", "External"),
            "url": e.get("event_url"),
            "status": e.get("status")
        })
        
    return results


@router.get("/resources/recommended")
async def get_recommended_resources(
    limit: int = Query(3, ge=1, le=10),
    current_user=Depends(get_current_user)
):
    """
    Get recommended learning resources.
    Returns title, category, source, difficulty level, URL.
    """
    # For now we fetch trending tech news from the content collection.
    # We can enhance it by filtering based on user skills later.
    cursor = opportunities_content_collection().find().sort("published_at", -1).limit(limit)
    
    articles = await cursor.to_list(length=limit)
    
    results = []
    for a in articles:
        results.append({
            "id": str(a["_id"]),
            "title": a.get("title"),
            "category": a.get("topic", "Tech"),
            "source": a.get("publisher"),
            "difficulty": "All Levels", # default
            "url": a.get("url")
        })
        
    return results
