from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Hackathon(BaseModel):
    id: str
    title: str
    description: str
    organizer: str
    start_date: datetime
    end_date: datetime
    registration_deadline: datetime
    location: str
    is_virtual: bool
    prizes: List[str]
    skills: List[str]
    participants_count: int
    created_at: datetime
    updated_at: datetime

class HackathonListResponse(BaseModel):
    hackathons: List[Hackathon]
