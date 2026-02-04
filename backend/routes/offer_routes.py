from datetime import datetime
from html import escape
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from ..models import user as user_model
from ..models import application as application_model
from ..models import pipeline as pipeline_model
from ..models.notification import create_notification
from ..models.offer import offers_collection, default_history_entry
from ..models.thread import append_text_message
from ..schemas.offer_schema import (
    OfferCreateRequest,
    OfferListResponse,
    OfferSummary,
    OfferUpdateRequest,
)
from ..utils.dependencies import get_current_user
from ..utils.activity_logger import log_activity
from ..utils.ai_scorer import update_student_ai_profile

router = APIRouter(prefix="/offers", tags=["offers"])

STATUS_SENT = "sent"
STATUS_WITHDRAWN = "withdrawn"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"


def sanitize_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = escape(value.strip())
    return cleaned or None


def serialize_offer(doc: dict) -> OfferSummary:
    return OfferSummary(
        id=str(doc["_id"]),
        candidate_id=str(doc["candidate_id"]),
        recruiter_id=str(doc["recruiter_id"]),
        job_id=str(doc["job_id"]) if doc.get("job_id") else None,
        package=doc["package"],
        expires_at=doc.get("expires_at"),
        status=doc["status"],
        notes=doc.get("notes"),
        thread_id=str(doc["thread_id"]) if doc.get("thread_id") else None,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def fetch_user(user_id: str) -> dict:
    user = await user_model.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


async def ensure_recruiter(current_user: dict):
    if current_user.get("role") != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter access required.")


async def ensure_participant(doc: dict, current_user: dict):
    current_id = str(current_user["_id"])
    if current_id not in {str(doc["candidate_id"]), str(doc["recruiter_id"])}:
        raise HTTPException(status_code=403, detail="Forbidden.")


async def notify(user_id: str, kind: str, payload: dict):
    await create_notification(user_id, kind, payload)


@router.post("", response_model=OfferSummary)
async def create_offer(payload: OfferCreateRequest, current_user=Depends(get_current_user)):
    await ensure_recruiter(current_user)
    candidate = await fetch_user(payload.candidate_id)
    if str(candidate["_id"]) == str(current_user["_id"]):
        raise HTTPException(status_code=400, detail="Cannot send offer to self.")

    job_id = ObjectId(payload.job_id) if payload.job_id and ObjectId.is_valid(payload.job_id) else None
    thread_id = ObjectId(payload.thread_id) if payload.thread_id and ObjectId.is_valid(payload.thread_id) else None

    doc = {
        "candidate_id": ObjectId(payload.candidate_id),
        "recruiter_id": ObjectId(current_user["_id"]),
        "job_id": job_id,
        "thread_id": thread_id,
        "package": payload.package,
        "expires_at": payload.expires_at,
        "status": STATUS_SENT,
        "notes": sanitize_text(payload.notes),
        "history": [default_history_entry("sent", str(current_user["_id"]))],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await offers_collection().insert_one(doc)
    doc["_id"] = result.inserted_id

    if payload.thread_id:
        await append_text_message(
            payload.thread_id,
            str(current_user["_id"]),
            f"Offer sent to {candidate.get('full_name') or candidate.get('username')}."
        )

    await notify(str(candidate["_id"]), "offer_sent", {"offer_id": str(doc["_id"])})
    
    await log_activity(
        str(current_user["_id"]), 
        "OFFER_SENT", 
        {"offer_id": str(doc["_id"]), "candidate_id": str(candidate["_id"])}
    )
    
    # Auto-stage transition: Move application to offer stage (Module 5)
    if job_id:
        app = await application_model.get_application_by_job_student(
            str(job_id), payload.candidate_id
        )
        if app:
            # Link offer to application
            await application_model.set_offer_on_application(
                str(app["_id"]), str(doc["_id"])
            )
            
            # Get pipeline and find offer stage
            pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
            if pipeline:
                offer_stage = pipeline_model.get_stage_by_type(pipeline, "offer")
                if offer_stage and app["current_stage_id"] != offer_stage["id"]:
                    await application_model.move_application_stage(
                        application_id=str(app["_id"]),
                        new_stage_id=offer_stage["id"],
                        new_stage_name=offer_stage["name"],
                        changed_by=str(current_user["_id"]),
                        reason="Offer extended",
                        student_visible_stage=offer_stage.get("student_visible_name", "Offer Received")
                    )
    
    return serialize_offer(doc)


def role_query(current_user: dict):
    if current_user.get("role") == "recruiter":
        return {"recruiter_id": ObjectId(current_user["_id"])}
    return {"candidate_id": ObjectId(current_user["_id"])}


@router.get("/my", response_model=OfferListResponse)
async def list_offers(current_user=Depends(get_current_user)):
    cursor = (
        offers_collection()
        .find(role_query(current_user))
        .sort("updated_at", -1)
    )
    docs = await cursor.to_list(length=None)
    return OfferListResponse(offers=[serialize_offer(doc) for doc in docs])


async def get_offer_or_404(offer_id: str) -> dict:
    if not ObjectId.is_valid(offer_id):
        raise HTTPException(status_code=404, detail="Offer not found.")
    doc = await offers_collection().find_one({"_id": ObjectId(offer_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Offer not found.")
    return doc


@router.get("/{offer_id}", response_model=OfferSummary)
async def get_offer(offer_id: str, current_user=Depends(get_current_user)):
    doc = await get_offer_or_404(offer_id)
    await ensure_participant(doc, current_user)
    return serialize_offer(doc)


async def update_offer_status(doc: dict, status: str, actor_id: str, meta=None):
    update = {
        "status": status,
        "updated_at": datetime.utcnow(),
        "history": doc.get("history", []) + [default_history_entry(status, actor_id, meta)],
    }
    await offers_collection().update_one({"_id": doc["_id"]}, {"$set": update})
    doc.update(update)


@router.post("/{offer_id}/accept", response_model=OfferSummary)
async def accept_offer(offer_id: str, current_user=Depends(get_current_user)):
    doc = await get_offer_or_404(offer_id)
    if str(doc["candidate_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only candidate can accept.")
    if doc["status"] not in {STATUS_SENT, STATUS_WITHDRAWN}:
        raise HTTPException(status_code=400, detail="Offer cannot be accepted.")
    await update_offer_status(doc, STATUS_ACCEPTED, str(current_user["_id"]))
    await notify(str(doc["recruiter_id"]), "offer_accepted", {"offer_id": offer_id})
    if doc.get("thread_id"):
        await append_text_message(doc["thread_id"], str(current_user["_id"]), "Offer accepted.")
    
    await log_activity(
        str(current_user["_id"]), 
        "OFFER_ACCEPTED", 
        {"offer_id": offer_id}
    )
    
    # Recalculate student AI profile
    await update_student_ai_profile(str(doc["candidate_id"]))
    
    # Auto-stage transition: Move to Hired (Module 5)
    if doc.get("job_id"):
        app = await application_model.get_application_by_job_student(
            str(doc["job_id"]), str(doc["candidate_id"])
        )
        if app:
            pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
            if pipeline:
                hired_stage = pipeline_model.get_stage_by_type(pipeline, "hired")
                if hired_stage:
                    await application_model.move_application_stage(
                        application_id=str(app["_id"]),
                        new_stage_id=hired_stage["id"],
                        new_stage_name=hired_stage["name"],
                        changed_by=str(current_user["_id"]),
                        reason="Offer accepted",
                        student_visible_stage="Hired"
                    )
                    await application_model.update_application_status(
                        str(app["_id"]), "hired", str(current_user["_id"])
                    )
    
    return serialize_offer(doc)


@router.post("/{offer_id}/reject", response_model=OfferSummary)
async def reject_offer(offer_id: str, current_user=Depends(get_current_user)):
    doc = await get_offer_or_404(offer_id)
    if str(doc["candidate_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only candidate can reject.")
    if doc["status"] != STATUS_SENT:
        raise HTTPException(status_code=400, detail="Offer cannot be rejected.")
    await update_offer_status(doc, STATUS_REJECTED, str(current_user["_id"]))
    await notify(str(doc["recruiter_id"]), "offer_rejected", {"offer_id": offer_id})
    if doc.get("thread_id"):
        await append_text_message(doc["thread_id"], str(current_user["_id"]), "Offer rejected.")
    
    await log_activity(
        str(current_user["_id"]), 
        "OFFER_REJECTED", 
        {"offer_id": offer_id}
    )
    
    # Recalculate student AI profile
    await update_student_ai_profile(str(doc["candidate_id"]))
    
    # Auto-stage transition: Move to Rejected/Offer Declined (Module 5)
    if doc.get("job_id"):
        app = await application_model.get_application_by_job_student(
            str(doc["job_id"]), str(doc["candidate_id"])
        )
        if app:
            pipeline = await pipeline_model.get_pipeline_by_id(str(app["pipeline_template_id"]))
            if pipeline:
                rejected_stage = pipeline_model.get_stage_by_type(pipeline, "rejected")
                if rejected_stage:
                    await application_model.move_application_stage(
                        application_id=str(app["_id"]),
                        new_stage_id=rejected_stage["id"],
                        new_stage_name="Offer Declined",
                        changed_by=str(current_user["_id"]),
                        reason="Offer rejected by candidate",
                        student_visible_stage="Not Selected"
                    )
                    await application_model.update_application_status(
                        str(app["_id"]), "rejected", str(current_user["_id"])
                    )
    
    return serialize_offer(doc)


@router.put("/{offer_id}", response_model=OfferSummary)
async def update_offer(
    offer_id: str,
    payload: OfferUpdateRequest,
    current_user=Depends(get_current_user),
):
    doc = await get_offer_or_404(offer_id)
    if str(doc["recruiter_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Recruiter access required.")

    updates = {}
    if payload.package:
        updates["package"] = payload.package
    if payload.expires_at is not None:
        updates["expires_at"] = payload.expires_at
    if payload.notes is not None:
        updates["notes"] = sanitize_text(payload.notes)
    if payload.status:
        if payload.status not in {STATUS_SENT, STATUS_WITHDRAWN}:
            raise HTTPException(status_code=400, detail="Invalid status.")
        updates["status"] = payload.status

    if not updates:
        return serialize_offer(doc)

    updates["updated_at"] = datetime.utcnow()
    history_entry = default_history_entry("updated", str(current_user["_id"]), {"updates": list(updates.keys())})
    await offers_collection().update_one(
        {"_id": doc["_id"]},
        {"$set": updates, "$push": {"history": history_entry}},
    )
    doc.update(updates)
    doc.setdefault("history", []).append(history_entry)

    target = str(doc["candidate_id"])
    await notify(target, "offer_updated", {"offer_id": offer_id})
    return serialize_offer(doc)


