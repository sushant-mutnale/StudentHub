"""
Smart Notification Routes
API endpoints for the intelligent notification system.
Module 4 Week 3: Notification management and preferences.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from bson import ObjectId

from ..services.notification_service import notification_service, DEFAULT_SETTINGS
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/smart-notifications", tags=["smart-notifications"])


# ============ Request/Response Models ============

class NotificationSettings(BaseModel):
    opportunities: Optional[dict] = None
    deadlines: Optional[dict] = None
    learning: Optional[dict] = None
    recruiter_activity: Optional[dict] = None
    achievements: Optional[dict] = None
    channels: Optional[dict] = None


# ============ Notification Endpoints ============

@router.get("/my")
async def get_my_notifications(
    unread_only: bool = Query(False, description="Only show unread"),
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    current_user=Depends(get_current_user)
):
    """
    Get notifications for the current user.
    Supports filtering by read status and type.
    """
    student_id = str(current_user["_id"])
    
    result = await notification_service.get_user_notifications(
        user_id=student_id,
        unread_only=unread_only,
        limit=limit,
        skip=skip,
        notification_type=notification_type
    )
    
    return {
        "status": "success",
        **result
    }


@router.post("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str,
    current_user=Depends(get_current_user)
):
    """Mark a specific notification as read."""
    student_id = str(current_user["_id"])
    
    success = await notification_service.mark_as_read(notification_id, student_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or already read")
    
    return {"status": "success", "notification_id": notification_id}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user=Depends(get_current_user)
):
    """Mark all notifications as read."""
    student_id = str(current_user["_id"])
    
    count = await notification_service.mark_all_as_read(student_id)
    
    return {
        "status": "success",
        "marked_count": count
    }


@router.post("/{notification_id}/click")
async def click_notification(
    notification_id: str,
    current_user=Depends(get_current_user)
):
    """
    Record a notification click.
    Also marks as read.
    """
    student_id = str(current_user["_id"])
    
    success = await notification_service.click_notification(notification_id, student_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"status": "clicked", "notification_id": notification_id}


@router.delete("/{notification_id}")
async def dismiss_notification(
    notification_id: str,
    current_user=Depends(get_current_user)
):
    """Dismiss a notification (remove from list)."""
    student_id = str(current_user["_id"])
    
    success = await notification_service.dismiss_notification(notification_id, student_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"status": "dismissed", "notification_id": notification_id}


# ============ Settings Endpoints ============

@router.get("/settings")
async def get_notification_settings(
    current_user=Depends(get_current_user)
):
    """
    Get notification preferences.
    Controls which notifications the user receives.
    """
    student_id = str(current_user["_id"])
    
    settings = await notification_service.get_user_settings(student_id)
    
    return {
        "status": "success",
        "settings": settings,
        "default_settings": DEFAULT_SETTINGS
    }


@router.put("/settings")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user=Depends(get_current_user)
):
    """
    Update notification preferences.
    
    Example body:
    {
        "opportunities": {"enabled": true, "min_score_threshold": 80},
        "deadlines": {"enabled": true, "advance_notice_days": 2},
        "learning": {"enabled": false}
    }
    """
    student_id = str(current_user["_id"])
    
    # Merge with existing settings
    current = await notification_service.get_user_settings(student_id)
    
    updated = {**current}
    if settings.opportunities:
        updated["opportunities"] = {**updated.get("opportunities", {}), **settings.opportunities}
    if settings.deadlines:
        updated["deadlines"] = {**updated.get("deadlines", {}), **settings.deadlines}
    if settings.learning:
        updated["learning"] = {**updated.get("learning", {}), **settings.learning}
    if settings.recruiter_activity:
        updated["recruiter_activity"] = {**updated.get("recruiter_activity", {}), **settings.recruiter_activity}
    if settings.achievements:
        updated["achievements"] = {**updated.get("achievements", {}), **settings.achievements}
    if settings.channels:
        updated["channels"] = {**updated.get("channels", {}), **settings.channels}
    
    result = await notification_service.update_user_settings(student_id, updated)
    
    return result


# ============ Stats Endpoints ============

@router.get("/stats")
async def get_notification_stats(
    current_user=Depends(get_current_user)
):
    """
    Get notification statistics.
    Shows engagement metrics and breakdown by type.
    """
    student_id = str(current_user["_id"])
    
    stats = await notification_service.get_notification_stats(student_id)
    
    return {
        "status": "success",
        "stats": stats
    }


# ============ Admin/Trigger Endpoints ============

@router.post("/trigger/opportunity-check")
async def trigger_opportunity_check(
    current_user=Depends(get_current_user)
):
    """
    Manually trigger opportunity match notifications.
    Admin/demo endpoint.
    """
    result = await notification_service.check_opportunity_matches()
    return {"status": "completed", **result}


@router.post("/trigger/deadline-check")
async def trigger_deadline_check(
    current_user=Depends(get_current_user)
):
    """
    Manually trigger deadline reminder notifications.
    Admin/demo endpoint.
    """
    result = await notification_service.check_deadline_reminders()
    return {"status": "completed", **result}


@router.post("/trigger/learning-check")
async def trigger_learning_check(
    current_user=Depends(get_current_user)
):
    """
    Manually trigger learning reminder notifications.
    Admin/demo endpoint.
    """
    result = await notification_service.check_learning_reminders()
    return {"status": "completed", **result}


@router.post("/trigger/all")
async def trigger_all_checks(
    current_user=Depends(get_current_user)
):
    """
    Run all notification trigger checks.
    Admin/demo endpoint.
    """
    result = await notification_service.run_all_checks()
    return {"status": "completed", **result}


# ============ Demo Endpoints ============

@router.get("/demo/list")
async def demo_list_notifications():
    """Demo: Get sample notification structure."""
    return {
        "sample_notifications": [
            {
                "type": "opportunity_match",
                "priority": "high",
                "title": "New match: Backend Developer Intern",
                "message": "TechCorp - 87% match",
                "action_url": "/opportunities/jobs/123"
            },
            {
                "type": "deadline_reminder",
                "priority": "urgent",
                "title": "Application deadline approaching",
                "message": "Frontend Intern at WebDesign closes in 2 days"
            },
            {
                "type": "learning_reminder",
                "priority": "medium",
                "title": "Continue your learning path",
                "message": "Your Docker learning has been inactive for 10 days"
            },
            {
                "type": "recruiter_activity",
                "priority": "low",
                "title": "Google viewed your profile",
                "message": "Your profile was viewed by a recruiter"
            },
            {
                "type": "achievement",
                "priority": "low",
                "title": "🎉 Profile score improved!",
                "message": "Your AI profile score increased by 15 points"
            }
        ],
        "notification_types": [
            "opportunity_match",
            "deadline_reminder",
            "learning_reminder",
            "recruiter_activity",
            "achievement",
            "batch"
        ],
        "priority_levels": ["low", "medium", "high", "urgent"]
    }


@router.post("/demo/create")
async def demo_create_notification(
    title: str = Query(...),
    message: str = Query(...),
    notification_type: str = Query("system")
):
    """Demo: Create a test notification (requires auth)."""
    return {
        "note": "Use authenticated endpoint to create real notifications",
        "sample_request": {
            "title": title,
            "message": message,
            "type": notification_type
        }
    }
