from fastapi import APIRouter, Depends
from typing import List
from ..models import hackathon as hackathon_model
from ..schemas.hackathon_schema import HackathonListResponse, Hackathon
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/hackathons", tags=["hackathons"])

@router.get("/", response_model=List[dict]) 
async def list_hackathons(current_user=Depends(get_current_user)):
    """List all available hackathons."""
    # Ensure some data exists
    await hackathon_model.seed_default_hackathons()
    
    hackathons = await hackathon_model.list_hackathons()
    
    # Convert ObjectIds to strings for response
    results = []
    for h in hackathons:
        h["id"] = str(h["_id"])
        if "_id" in h: del h["_id"]
        results.append(h)
        
    return results
