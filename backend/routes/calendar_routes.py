"""
Calendar Routes

Aggregates a student's deadlines and events (opportunity deadlines, application
dates, interviews) and exposes them as a JSON list and as an iCalendar (.ics)
download for use with Google Calendar / Outlook.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services.opportunity_ingestion import opportunities_jobs_collection
from ..database import get_database
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    kind: str  # job, hackathon, application, interview
    url: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class DeadlinesResponse(BaseModel):
    events: List[CalendarEvent] = Field(default_factory=list)
    total: int = 0


async def _collect_events(student, now: datetime) -> List[dict]:
    events: List[dict] = []

    # 1. Opportunity jobs with apply-by deadlines
    try:
        cursor = opportunities_jobs_collection().find(
            {"apply_by": {"$gte": now, "$exists": True}, "is_active": True}
        )
        for job in await cursor.to_list(length=500):
            events.append({
                "id": f"job_{job['_id']}",
                "title": f"Apply: {job.get('title', 'Job')}" + (
                    f" - {job.get('company')}" if job.get("company") else ""
                ),
                "start": job["apply_by"],
                "end": job["apply_by"] + timedelta(hours=1),
                "kind": "job",
                "url": f"/jobs/{job['_id']}",
                "location": job.get("location"),
                "description": f"Application deadline for {job.get('title', '')}.",
            })
    except Exception:
        pass

    # 2. Hackathons with registration deadlines
    try:
        db = get_database()
        if "hackathons" in db.list_collection_names() or True:
            h_cursor = db["hackathons"].find(
                {"registration_deadline": {"$gte": now, "$exists": True}}
            )
            for hack in await h_cursor.to_list(length=200):
                events.append({
                    "id": f"hack_{hack['_id']}",
                    "title": f"Register: {hack.get('name', hack.get('event_name', 'Hackathon'))}",
                    "start": hack["registration_deadline"],
                    "end": hack["registration_deadline"] + timedelta(hours=1),
                    "kind": "hackathon",
                    "url": f"/opportunities?tab=hackathons",
                    "description": f"Registration deadline for hackathon.",
                })
    except Exception:
        pass

    # 3. Scheduled interviews for this student
    try:
        db = get_database()
        i_cursor = db["interviews"].find(
            {"candidate_id": ObjectId(student["_id"]), "scheduled_at": {"$gte": now}}
        )
        for interview in await i_cursor.to_list(length=100):
            start = interview.get("scheduled_at")
            events.append({
                "id": f"interview_{interview['_id']}",
                "title": f"Interview: {interview.get('job_title', 'Interview')}",
                "start": start,
                "end": start + timedelta(hours=1),
                "kind": "interview",
                "url": f"/interviews/{interview['_id']}",
                "description": interview.get("notes") or "Scheduled interview.",
            })
    except Exception:
        pass

    events.sort(key=lambda e: e["start"])
    return events


def _to_ics(events: List[dict]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StudentHub//DeadlineCalendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev['id']}@studenthub")
        lines.append(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTSTART:{ev['start'].strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTEND:{ev['end'].strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"SUMMARY:{_sanitize_ics(ev['title'])}")
        if ev.get("description"):
            lines.append(f"DESCRIPTION:{_sanitize_ics(ev['description'])}")
        if ev.get("location"):
            lines.append(f"LOCATION:{_sanitize_ics(ev['location'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def _sanitize_ics(text: str) -> str:
    return (text or "").replace("\n", " ").replace("\r", "").replace(",", "\\,")


@router.get("/deadlines", response_model=DeadlinesResponse)
async def get_deadlines(
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    """Return the current user's upcoming deadlines and events."""
    now = datetime.utcnow()
    events = await _collect_events(current_user, now)
    return DeadlinesResponse(
        events=[CalendarEvent(**e) for e in events[:limit]],
        total=len(events),
    )


@router.get("/deadlines/ical")
async def get_deadlines_ical(
    current_user=Depends(get_current_user),
):
    """Download the user's deadlines as an iCalendar (.ics) feed."""
    now = datetime.utcnow()
    events = await _collect_events(current_user, now)
    ics = _to_ics(events)
    return Response(
        content=ics,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=studenthub-deadlines.ics"},
    )
