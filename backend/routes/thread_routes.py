from datetime import datetime
from html import escape
from typing import Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import user as user_model
from ..models.thread import (
    build_participant_hash,
    messages_collection,
    threads_collection,
)
from ..schemas.thread_schema import (
    ThreadCreateRequest,
    ThreadDetailResponse,
    ThreadListResponse,
    ThreadMessage,
    ThreadMessageCreate,
    ThreadSummary,
    ThreadParticipant,
)
from ..utils.dependencies import get_current_user

router = APIRouter()


def sanitize_text(text: str) -> str:
    cleaned = escape(text.strip())
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message text cannot be empty.",
        )
    return cleaned


def object_id_or_404(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=404, detail="Invalid identifier supplied.")
    return ObjectId(id_str)


async def ensure_thread_for_user(thread_id: str, user_id: str) -> dict:
    thread_obj_id = object_id_or_404(thread_id)
    thread = await threads_collection().find_one({"_id": thread_obj_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")
    participant_ids = {str(pid) for pid in thread.get("participants", [])}
    if user_id not in participant_ids:
        raise HTTPException(status_code=403, detail="Forbidden.")
    return thread


async def build_participant_profiles(participant_ids: List[str]) -> List[ThreadParticipant]:
    users = await user_model.get_users_by_ids(participant_ids)
    user_map: Dict[str, dict] = {str(doc["_id"]): doc for doc in users}
    participants: List[ThreadParticipant] = []
    for pid in participant_ids:
        doc = user_map.get(pid)
        if not doc:
            continue
        participants.append(
            ThreadParticipant(
                id=pid,
                username=doc.get("username"),
                full_name=doc.get("full_name") or doc.get("company_name"),
                role=doc.get("role"),
            )
        )
    return participants


def serialize_thread_summary(thread: dict, participants: List[ThreadParticipant], current_user_id: str) -> ThreadSummary:
    unread_counts = thread.get("unread_counts", {})
    return ThreadSummary(
        id=str(thread["_id"]),
        participants=participants,
        last_message_preview=thread.get("last_message_preview"),
        last_message_at=thread.get("last_message_at"),
        unread_count=unread_counts.get(current_user_id, 0),
    )


def serialize_message(doc: dict) -> ThreadMessage:
    return ThreadMessage(
        id=str(doc["_id"]),
        thread_id=str(doc["thread_id"]),
        sender_id=str(doc["sender_id"]),
        text=doc.get("text"),
        created_at=doc.get("created_at"),
        read_by=[str(user_id) for user_id in doc.get("read_by", [])],
    )


async def increment_unread_counts(thread: dict, sender_id: str, last_text: str, timestamp: datetime):
    unread_counts = thread.get("unread_counts", {})
    participants = [str(pid) for pid in thread.get("participants", [])]
    for pid in participants:
        if pid == sender_id:
            unread_counts[pid] = 0
        else:
            unread_counts[pid] = unread_counts.get(pid, 0) + 1
    update = {
        "last_message_at": timestamp,
        "last_message_preview": last_text[:140],
        "unread_counts": unread_counts,
        "updated_at": timestamp,
    }
    await threads_collection().update_one({"_id": thread["_id"]}, {"$set": update})
    thread.update(update)


async def append_message(thread: dict, sender_id: str, text: str) -> dict:
    sender_obj = object_id_or_404(sender_id)
    now = datetime.utcnow()
    message_doc = {
        "thread_id": thread["_id"],
        "sender_id": sender_obj,
        "text": text,
        "created_at": now,
        "read_by": [sender_obj],
    }
    insert_result = await messages_collection().insert_one(message_doc)
    message_doc["_id"] = insert_result.inserted_id
    await increment_unread_counts(thread, sender_id, text, now)
    return message_doc


async def resolve_participant_ids(
    request: ThreadCreateRequest, current_user_id: str
) -> List[str]:
    participant_ids: set[str] = set()
    if request.participant_ids:
        for pid in request.participant_ids:
            if not ObjectId.is_valid(pid):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid participant id: {pid}",
                )
            participant_ids.add(pid)

    if request.participant_usernames:
        users = await user_model.get_users_by_usernames(request.participant_usernames)
        found_usernames = {user["username"] for user in users}
        missing = [
            username
            for username in request.participant_usernames
            if username not in found_usernames
        ]
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Users not found: {', '.join(missing)}",
            )
        for user in users:
            participant_ids.add(str(user["_id"]))

    participant_ids.add(current_user_id)

    if len(participant_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threads require at least two unique participants.",
        )

    # Ensure every provided id maps to a real user
    users = await user_model.get_users_by_ids(list(participant_ids))
    found_ids = {str(user["_id"]) for user in users}
    missing_ids = [pid for pid in participant_ids if pid not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Users not found for ids: {', '.join(missing_ids)}",
        )

    return list(participant_ids)


@router.post("/threads", response_model=ThreadSummary)
async def create_thread(
    payload: ThreadCreateRequest, current_user=Depends(get_current_user)
):
    current_user_id = str(current_user["_id"])
    participant_ids = await resolve_participant_ids(payload, current_user_id)
    participant_oids = [ObjectId(pid) for pid in participant_ids]
    participant_hash = build_participant_hash(participant_ids)

    thread = await threads_collection().find_one({"participant_hash": participant_hash})
    if not thread:
        now = datetime.utcnow()
        thread_doc = {
            "participants": participant_oids,
            "participant_hash": participant_hash,
            "created_at": now,
            "updated_at": now,
            "last_message_at": None,
            "last_message_preview": None,
            "unread_counts": {pid: 0 for pid in participant_ids},
        }
        insert_result = await threads_collection().insert_one(thread_doc)
        thread = {**thread_doc, "_id": insert_result.inserted_id}

    if payload.initial_message:
        text = sanitize_text(payload.initial_message)
        await append_message(thread, current_user_id, text)

    participants = await build_participant_profiles(
        [str(pid) for pid in thread["participants"]]
    )
    return serialize_thread_summary(thread, participants, current_user_id)


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(current_user=Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    cursor = (
        threads_collection()
        .find({"participants": ObjectId(current_user_id)})
        .sort("last_message_at", -1)
    )
    threads = await cursor.to_list(length=None)
    all_participant_ids = []
    for thread in threads:
        all_participant_ids.extend(str(pid) for pid in thread.get("participants", []))
    unique_ids = list(dict.fromkeys(all_participant_ids))
    participants_map = await build_participant_profiles(unique_ids)
    participant_lookup = {participant.id: participant for participant in participants_map}

    summaries: List[ThreadSummary] = []
    for thread in threads:
        participant_ids = [str(pid) for pid in thread.get("participants", [])]
        participants = [
            participant_lookup[pid]
            for pid in participant_ids
            if pid in participant_lookup
        ]
        summaries.append(serialize_thread_summary(thread, participants, current_user_id))
    return ThreadListResponse(threads=summaries)


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: str,
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    current_user_id = str(current_user["_id"])
    thread = await ensure_thread_for_user(thread_id, current_user_id)
    participant_ids = [str(pid) for pid in thread.get("participants", [])]
    participants = await build_participant_profiles(participant_ids)

    cursor = (
        messages_collection()
        .find({"thread_id": thread["_id"]})
        .sort("created_at", 1)
        .skip(skip)
        .limit(limit + 1)
    )
    docs = await cursor.to_list(length=limit + 1)
    has_more = len(docs) > limit
    if has_more:
        docs = docs[:-1]

    messages = [serialize_message(doc) for doc in docs]
    return ThreadDetailResponse(
        thread=serialize_thread_summary(thread, participants, current_user_id),
        messages=messages,
        has_more=has_more,
    )


@router.post("/threads/{thread_id}/messages", response_model=ThreadMessage)
async def send_message(
    thread_id: str,
    payload: ThreadMessageCreate,
    current_user=Depends(get_current_user),
):
    current_user_id = str(current_user["_id"])
    thread = await ensure_thread_for_user(thread_id, current_user_id)
    text = sanitize_text(payload.text)
    message_doc = await append_message(thread, current_user_id, text)
    return serialize_message(message_doc)


@router.put("/threads/{thread_id}/read")
async def mark_thread_read(thread_id: str, current_user=Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    thread = await ensure_thread_for_user(thread_id, current_user_id)
    unread_counts = thread.get("unread_counts", {})
    if unread_counts.get(current_user_id, 0) > 0:
        unread_counts[current_user_id] = 0
        await threads_collection().update_one(
            {"_id": thread["_id"]},
            {"$set": {"unread_counts": unread_counts, "updated_at": datetime.utcnow()}},
        )

    await messages_collection().update_many(
        {"thread_id": thread["_id"]},
        {"$addToSet": {"read_by": ObjectId(current_user_id)}},
    )
    return {"message": "Thread marked as read.", "thread_id": thread_id}



