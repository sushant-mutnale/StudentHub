import logging
from datetime import datetime
from html import escape
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

import logging

from ..config import settings
from ..models import user as user_model
from ..models import application as application_model
from ..models import pipeline as pipeline_model
from ..models.interview import (
    interviews_collection,
    default_history_entry,
)
from ..models.notification import create_notification
from ..models.thread import append_text_message, get_thread_by_id
from ..models.outbox import outbox
from ..events.event_bus import EventTypes
from ..schemas.interview_schema import (
    InterviewAcceptRequest,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewDeclineRequest,
    InterviewFeedbackRequest,
    InterviewListResponse,
    InterviewRescheduleRequest,
    InterviewSummary,
    TimeSlot,
)
from ..utils.calendar import build_ics_event
from ..utils.dependencies import get_current_user
from ..utils.email_send import send_generic_email
from ..utils.activity_logger import log_activity
from ..utils.ai_scorer import update_student_ai_profile

router = APIRouter(prefix="/interviews", tags=["interviews"])
logger = logging.getLogger(__name__)

STATUS_PROPOSED = "proposed"
STATUS_SCHEDULED = "scheduled"
STATUS_RESCHEDULED = "rescheduled"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_DECLINED = "declined"

ALLOWED_STATUSES = {
    STATUS_PROPOSED,
    STATUS_SCHEDULED,
    STATUS_RESCHEDULED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    STATUS_DECLINED,
}


def resolve_frontend_base_url() -> str:
    """
    Determine which frontend base URL to use when building interview links.
    Preference order:
        1. settings.frontend_base_url (if defined)
        2. settings.frontend_origin (legacy env)
        3. Default dev fallback http://localhost:5173
    """
    base = (
        getattr(settings, "frontend_base_url", None)
        or getattr(settings, "frontend_origin", None)
        or "http://localhost:5173"
    )
    normalized = str(base).rstrip("/")
    logger.debug("Interview link base resolved to %s", normalized)
    return normalized


def sanitize_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = escape(value.strip())
    return cleaned or None


def serialize_slot(slot: Optional[dict]) -> Optional[TimeSlot]:
    if not slot:
        return None
    return TimeSlot(**slot)


def serialize_interview(doc: dict) -> InterviewSummary:
    return InterviewSummary(
        id=str(doc["_id"]),
        candidate_id=str(doc["candidate_id"]),
        recruiter_id=str(doc["recruiter_id"]),
        job_id=str(doc["job_id"]) if doc.get("job_id") else None,
        status=doc["status"],
        scheduled_slot=serialize_slot(doc.get("scheduled_slot")),
        proposed_times=[TimeSlot(**slot) for slot in doc.get("proposed_times", [])],
        location=doc.get("location"),
        description=doc.get("description"),
        thread_id=str(doc["thread_id"]) if doc.get("thread_id") else None,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def fetch_user(user_id: str) -> dict:
    user = await user_model.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def ensure_object_id(value: Optional[str], field: str) -> Optional[ObjectId]:
    if not value:
        return None
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail=f"Invalid {field}.")
    return ObjectId(value)


def pick_slot_from_payload(doc: dict, payload: InterviewAcceptRequest) -> dict:
    slots = doc.get("proposed_times", [])
    if payload.slot_index is not None:
        if payload.slot_index < 0 or payload.slot_index >= len(slots):
            raise HTTPException(status_code=400, detail="Invalid slot index.")
        return slots[payload.slot_index]
    if payload.selected_slot:
        candidate = payload.selected_slot.model_dump()
        for slot in slots:
            if (
                slot["start"] == candidate["start"]
                and slot["end"] == candidate["end"]
                and slot.get("timezone", "UTC") == candidate.get("timezone", "UTC")
            ):
                return slot
        raise HTTPException(status_code=400, detail="Selected slot not found.")
    raise HTTPException(status_code=400, detail="Provide slot_index or selected_slot.")


async def ensure_participant(doc: dict, current_user: dict):
    current_id = str(current_user["_id"])
    if current_id not in {str(doc["candidate_id"]), str(doc["recruiter_id"])}:
        raise HTTPException(status_code=403, detail="Forbidden.")


async def ensure_recruiter(current_user: dict):
    if current_user.get("role") != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter access required.")


async def ensure_candidate(doc: dict, current_user: dict):
    if str(doc["candidate_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only candidate can perform this action.")


async def notify_users(user_ids: List[str], kind: str, payload: dict):
    for user_id in user_ids:
        await create_notification(user_id, kind, payload)


async def append_thread_event(thread_id: Optional[str], sender_id: str, text: str):
    if not thread_id:
        return
    await append_text_message(thread_id, sender_id, text)


logger = logging.getLogger(__name__)


def resolve_frontend_base_url() -> str:
    base = getattr(settings, "frontend_base_url", None) or getattr(
        settings, "frontend_origin", None
    )
    if not base:
        base = "http://localhost:5173"
    base = str(base).rstrip("/")
    logger.debug("Interview links will use frontend base: %s", base)
    return base


def email_task(background_tasks: BackgroundTasks, to_email: str, subject: str, html: str, attachments=None):
    text = html.replace("<br>", "\n")
    background_tasks.add_task(send_generic_email, to_email, subject, html, text, attachments)


@router.post("", response_model=InterviewSummary)
async def create_interview(
    payload: InterviewCreateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    await ensure_recruiter(current_user)
    if not payload.proposed_times:
        raise HTTPException(status_code=400, detail="At least one proposed slot is required.")

    candidate = await fetch_user(payload.candidate_id)
    if str(candidate["_id"]) == str(current_user["_id"]):
        raise HTTPException(status_code=400, detail="Candidate and recruiter cannot be the same user.")

    job_id = ensure_object_id(payload.job_id, "job_id")
    thread_id = ensure_object_id(payload.thread_id, "thread_id")

    doc = {
        "candidate_id": ObjectId(payload.candidate_id),
        "recruiter_id": ObjectId(current_user["_id"]),
        "job_id": job_id,
        "thread_id": thread_id,
        "proposed_by": ObjectId(current_user["_id"]),
        "proposed_times": [slot.model_dump() for slot in payload.proposed_times],
        "scheduled_slot": None,
        "location": payload.location.model_dump(),
        "status": STATUS_PROPOSED,
        "description": sanitize_text(payload.description),
        "feedback": [],
        "history": [
            default_history_entry(
                "proposed",
                str(current_user["_id"]),
                {"times": [slot.model_dump() for slot in payload.proposed_times]},
            )
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await interviews_collection().insert_one(doc)
    doc["_id"] = result.inserted_id

    await notify_users(
        [str(candidate["_id"])],
        "interview_proposed",
        {"interview_id": str(doc["_id"])},
    )

    await append_thread_event(
        payload.thread_id,
        str(current_user["_id"]),
        f"Interview proposed with {candidate.get('full_name') or candidate.get('username')} "
        f"for slots: {', '.join(slot.start.isoformat() for slot in payload.proposed_times)}",
    )

    base_url = resolve_frontend_base_url()
    interview_url = f"{base_url}/interviews/{doc['_id']}"
    html = (
        f"<p>Hi {candidate.get('full_name') or candidate.get('username')},</p>"
        "<p>You have a new interview proposal on StudentHub. "
        f"<a href=\"{interview_url}\">View details</a>.</p>"
    )
    background_tasks.add_task(
        send_generic_email,
        candidate["email"],
        "New interview proposal on StudentHub",
        html,
        f"View interview details: {interview_url}",
        None,
    )

    await log_activity(
        str(current_user["_id"]), 
        "INTERVIEW_PROPOSED", 
        {"interview_id": str(doc["_id"]), "candidate_id": payload.candidate_id}
    )

    # Auto-stage transition: Move application to interview stage (Module 5)
    if job_id:
        app = await application_model.get_application_by_job_student(
            str(job_id), payload.candidate_id
        )
        if app:
            # Link interview to application
            await application_model.add_interview_to_application(
                str(app["_id"]), str(doc["_id"])
            )
            
            # Get pipeline and find next interview stage
            pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
            if pipeline:
                interview_stage = pipeline_model.get_stage_by_type(pipeline, "interview")
                if interview_stage and app["current_stage_id"] != interview_stage["id"]:
                    await application_model.move_application_stage(
                        application_id=str(app["_id"]),
                        new_stage_id=interview_stage["id"],
                        new_stage_name=interview_stage["name"],
                        changed_by=str(current_user["_id"]),
                        reason="Interview scheduled",
                        student_visible_stage=interview_stage.get("student_visible_name", "Interview Scheduled")
                    )

    return serialize_interview(doc)


@router.get("/my", response_model=InterviewListResponse)
async def list_my_interviews(
    status_filter: Optional[str] = Query(default=None),
    upcoming_only: bool = False,
    current_user=Depends(get_current_user),
):
    query = {}
    current_id = ObjectId(current_user["_id"])
    if current_user.get("role") == "recruiter":
        query["recruiter_id"] = current_id
    else:
        query["candidate_id"] = current_id

    if status_filter:
        if status_filter not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter.")
        query["status"] = status_filter

    if upcoming_only:
        query["scheduled_slot.start"] = {"$gte": datetime.utcnow()}

    cursor = (
        interviews_collection()
        .find(query)
        .sort("updated_at", -1)
    )
    docs = await cursor.to_list(length=None)
    return InterviewListResponse(interviews=[serialize_interview(doc) for doc in docs])


async def get_interview_or_404(interview_id: str) -> dict:
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=404, detail="Interview not found.")
    doc = await interviews_collection().find_one({"_id": ObjectId(interview_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return doc


@router.get("/{interview_id}", response_model=InterviewSummary)
async def get_interview(interview_id: str, current_user=Depends(get_current_user)):
    doc = await get_interview_or_404(interview_id)
    await ensure_participant(doc, current_user)
    return serialize_interview(doc)


@router.post("/{interview_id}/accept", response_model=InterviewSummary)
async def accept_interview(
    interview_id: str,
    payload: InterviewAcceptRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    doc = await get_interview_or_404(interview_id)
    await ensure_candidate(doc, current_user)
    slot = pick_slot_from_payload(doc, payload)

    update = {
        "scheduled_slot": slot,
        "status": STATUS_SCHEDULED,
        "updated_at": datetime.utcnow(),
        "history": doc.get("history", [])
        + [default_history_entry("accepted", str(current_user["_id"]), {"slot": slot})],
    }
    await interviews_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)

    recruiter = await user_model.get_user_by_id(str(doc["recruiter_id"]))
    candidate = await user_model.get_user_by_id(str(doc["candidate_id"]))

    # [TRANSACTIONAL OUTBOX] Publish interview scheduled event
    location_display = doc.get("location", {}).get("url") or doc.get("location", {}).get("address", "Online")
    await outbox.add_event(
        event_type=EventTypes.INTERVIEW_SCHEDULED,
        payload={
            "interview_id": interview_id,
            "candidate_id": str(doc["candidate_id"]),
            "student_id": str(doc["candidate_id"]),
            "recruiter_id": str(doc["recruiter_id"]),
            "student_name": candidate.get("full_name") or candidate.get("username"),
            "recruiter_email": recruiter["email"],
            "candidate_email": candidate["email"],
            "date": str(slot["start"]),
            "time": slot["start"].strftime("%H:%M"),
            "location": location_display
        },
        actor_id=str(current_user["_id"])
    )

    await notify_users(
        [str(doc["recruiter_id"])],
        "interview_scheduled",
        {"interview_id": interview_id},
    )
    await append_thread_event(
        doc.get("thread_id") and str(doc["thread_id"]),
        str(current_user["_id"]),
        f"Interview scheduled for {slot['start']} ({slot.get('timezone','UTC')}).",
    )

    if recruiter and candidate:
        ics_content = build_ics_event(
            f"interview-{interview_id}",
            "StudentHub Interview",
            doc.get("description") or "Interview via StudentHub",
            slot["start"],
            slot["end"],
            recruiter["email"],
            candidate["email"],
            location_display,
            slot.get("timezone", "UTC"),
        )
        base_url = resolve_frontend_base_url()
        interview_url = f"{base_url}/interviews/{interview_id}"
        html = (
            f"<p>Your interview has been scheduled.</p><p>Details: <a href=\"{interview_url}\">View interview</a></p>"
        )
        attachments = [("interview.ics", ics_content, "text/calendar")]
        email_task(background_tasks, candidate["email"], "Interview confirmed", html, attachments)
        email_task(background_tasks, recruiter["email"], "Interview confirmed", html, attachments)

    await log_activity(
        str(current_user["_id"]), 
        "INTERVIEW_ACCEPTED", 
        {"interview_id": interview_id}
    )

    return serialize_interview(doc)


@router.post("/{interview_id}/decline", response_model=InterviewSummary)
async def decline_interview(
    interview_id: str,
    payload: InterviewDeclineRequest,
    current_user=Depends(get_current_user),
):
    doc = await get_interview_or_404(interview_id)
    await ensure_candidate(doc, current_user)
    reason = sanitize_text(payload.reason)
    update = {
        "status": STATUS_DECLINED,
        "updated_at": datetime.utcnow(),
        "history": doc.get("history", [])
        + [default_history_entry("declined", str(current_user["_id"]), {"reason": reason})],
    }
    await interviews_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)
    await notify_users(
        [str(doc["recruiter_id"])],
        "interview_declined",
        {"interview_id": interview_id},
    )
    await append_thread_event(
        doc.get("thread_id") and str(doc["thread_id"]),
        str(current_user["_id"]),
        f"Interview declined. Reason: {reason or 'not provided.'}",
    )
    await log_activity(
        str(current_user["_id"]), 
        "INTERVIEW_DECLINED", 
        {"interview_id": interview_id}
    )
    return serialize_interview(doc)


@router.post("/{interview_id}/reschedule", response_model=InterviewSummary)
async def reschedule_interview(
    interview_id: str,
    payload: InterviewRescheduleRequest,
    current_user=Depends(get_current_user),
):
    doc = await get_interview_or_404(interview_id)
    await ensure_participant(doc, current_user)
    if not payload.proposed_times:
        raise HTTPException(status_code=400, detail="Provide proposed times.")
    update = {
        "status": STATUS_RESCHEDULED,
        "proposed_times": [slot.model_dump() for slot in payload.proposed_times],
        "scheduled_slot": None,
        "updated_at": datetime.utcnow(),
        "history": doc.get("history", [])
        + [
            default_history_entry(
                "rescheduled",
                str(current_user["_id"]),
                {"note": sanitize_text(payload.note)},
            )
        ],
    }
    await interviews_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)
    other_user = (
        str(doc["candidate_id"])
        if str(current_user["_id"]) == str(doc["recruiter_id"])
        else str(doc["recruiter_id"])
    )
    await notify_users(
        [other_user],
        "interview_rescheduled",
        {"interview_id": interview_id},
    )
    await append_thread_event(
        doc.get("thread_id") and str(doc["thread_id"]),
        str(current_user["_id"]),
        "Interview reschedule requested.",
    )
    return serialize_interview(doc)


@router.post("/{interview_id}/cancel", response_model=InterviewSummary)
async def cancel_interview(
    interview_id: str,
    payload: InterviewCancelRequest,
    current_user=Depends(get_current_user),
):
    doc = await get_interview_or_404(interview_id)
    await ensure_participant(doc, current_user)
    reason = sanitize_text(payload.reason)
    update = {
        "status": STATUS_CANCELLED,
        "updated_at": datetime.utcnow(),
        "history": doc.get("history", [])
        + [default_history_entry("cancelled", str(current_user["_id"]), {"reason": reason})],
    }
    await interviews_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)
    other_user = (
        str(doc["candidate_id"])
        if str(current_user["_id"]) == str(doc["recruiter_id"])
        else str(doc["recruiter_id"])
    )
    await notify_users(
        [other_user],
        "interview_cancelled",
        {"interview_id": interview_id},
    )
    await append_thread_event(
        doc.get("thread_id") and str(doc["thread_id"]),
        str(current_user["_id"]),
        f"Interview cancelled. Reason: {reason or 'not provided.'}",
    )
    await log_activity(
        str(current_user["_id"]), 
        "INTERVIEW_CANCELLED", 
        {"interview_id": interview_id}
    )
    return serialize_interview(doc)


@router.post("/{interview_id}/feedback", response_model=InterviewSummary)
async def submit_feedback(
    interview_id: str,
    payload: InterviewFeedbackRequest,
    current_user=Depends(get_current_user),
):
    doc = await get_interview_or_404(interview_id)
    await ensure_participant(doc, current_user)
    if str(current_user["_id"]) != str(doc["recruiter_id"]):
        raise HTTPException(status_code=403, detail="Only recruiter can submit feedback.")
    feedback_entry = {
        "submitted_by": ObjectId(current_user["_id"]),
        "rating": payload.rating,
        "comment": sanitize_text(payload.comment),
        "submitted_at": datetime.utcnow(),
    }
    update = {
        "feedback": doc.get("feedback", []) + [feedback_entry],
        "history": doc.get("history", [])
        + [default_history_entry("feedback_submitted", str(current_user["_id"]))],
        "updated_at": datetime.utcnow(),
    }
    await interviews_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)
    await notify_users(
        [str(doc["candidate_id"])],
        "interview_feedback",
        {"interview_id": interview_id},
    )
    await log_activity(
        str(current_user["_id"]), 
        "FEEDBACK_SUBMITTED", 
        {"interview_id": interview_id, "rating": payload.rating}
    )
    
    # Recalculate student AI profile
    await update_student_ai_profile(str(doc["candidate_id"]))
    
    return serialize_interview(doc)


