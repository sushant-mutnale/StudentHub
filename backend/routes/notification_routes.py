from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ..models import notification as notification_model
from ..schemas.notification_schema import NotificationResponse
from ..utils.dependencies import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/notifications", tags=["notifications"])

def db_to_notification_response(doc: dict) -> NotificationResponse:
    return NotificationResponse(
        id=str(doc["_id"]),
        kind=doc["kind"],
        payload=doc["payload"],
        is_read=doc["is_read"],
        read_at=doc.get("read_at"),
        priority=doc.get("priority", "medium"),
        category=doc.get("category", "general"),
        created_at=doc["created_at"]
    )

@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(current_user=Depends(get_current_user)):
    cursor = notification_model.notifications_collection().find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(length=None)
    return [db_to_notification_response(doc) for doc in docs]

@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user=Depends(get_current_user)):
    doc = await notification_model.notifications_collection().find_one({"_id": ObjectId(notification_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(doc["user_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await notification_model.mark_notification_as_read(notification_id)
    return {"status": "success"}

@router.put("/read-all")
async def mark_all_as_read(current_user=Depends(get_current_user)):
    from datetime import datetime
    await notification_model.notifications_collection().update_many(
        {"user_id": current_user["_id"], "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    return {"status": "success"}
