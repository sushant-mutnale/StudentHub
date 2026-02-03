"""
Notification Service
Smart notification system for opportunity alerts, deadline reminders,
learning nudges, and recruiter activity.

Module 4 Week 3: Complete notification infrastructure.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from bson import ObjectId

from ..database import get_database


# ============ Collections ============

def notifications_collection():
    return get_database()["notifications"]


def notification_settings_collection():
    return get_database()["notification_settings"]


def users_collection():
    return get_database()["users"]


def opportunities_jobs_collection():
    return get_database()["opportunities_jobs"]


def opportunities_hackathons_collection():
    return get_database()["opportunities_hackathons"]


def learning_paths_collection():
    return get_database()["learning_paths"]


# ============ Enums and Constants ============

class NotificationType(str, Enum):
    OPPORTUNITY_MATCH = "opportunity_match"
    DEADLINE_REMINDER = "deadline_reminder"
    LEARNING_REMINDER = "learning_reminder"
    RECRUITER_ACTIVITY = "recruiter_activity"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"
    BATCH = "batch"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationAction(str, Enum):
    CLICKED = "clicked"
    SAVED = "saved"
    APPLIED = "applied"
    IGNORED = "ignored"
    DISMISSED = "dismissed"


# Default notification settings
DEFAULT_SETTINGS = {
    "opportunities": {
        "enabled": True,
        "min_score_threshold": 75,
        "frequency": "instant",  # instant, daily, weekly
        "types": ["job", "hackathon"]
    },
    "deadlines": {
        "enabled": True,
        "advance_notice_days": 3
    },
    "learning": {
        "enabled": True,
        "reminder_frequency": "weekly",
        "inactive_days_threshold": 7
    },
    "recruiter_activity": {
        "enabled": True,
        "types": ["profile_view", "interview", "message", "offer"]
    },
    "achievements": {
        "enabled": True
    },
    "channels": {
        "in_app": True,
        "email": False,
        "push": False
    }
}


# ============ Notification Service ============

class NotificationService:
    """
    Manages creation, delivery, and tracking of notifications.
    Implements 5 trigger categories with batching and preferences.
    """
    
    def __init__(self):
        self.batch_threshold = 3  # Batch if more than 3 similar notifications
    
    # ============ Core Methods ============
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        action_url: str = None,
        action_text: str = None,
        related_entity: Dict = None,
        trigger_info: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user.
        Respects user preferences before creating.
        """
        user_id_obj = ObjectId(user_id)
        
        # Check if user has disabled this type
        settings = await self.get_user_settings(user_id)
        if not self._should_notify(settings, notification_type, category):
            return {"status": "skipped", "reason": "User disabled this notification type"}
        
        # Check if already notified (avoid duplicates)
        if related_entity:
            existing = await notifications_collection().find_one({
                "user_id": user_id_obj,
                "type": notification_type,
                "related_entity.entity_id": related_entity.get("entity_id"),
                "created_at": {"$gte": datetime.utcnow() - timedelta(days=1)}
            })
            if existing:
                return {"status": "skipped", "reason": "Already notified recently"}
        
        notification = {
            "user_id": user_id_obj,
            "user_type": "student",
            "type": notification_type,
            "category": category,
            "priority": priority,
            "title": title,
            "message": message,
            "action_url": action_url,
            "action_text": action_text,
            "related_entity": related_entity,
            "trigger": trigger_info,
            "created_at": datetime.utcnow(),
            "read_at": None,
            "clicked_at": None,
            "dismissed_at": None,
            "delivery_status": {
                "in_app": True,
                "email": False,
                "push": False
            }
        }
        
        result = await notifications_collection().insert_one(notification)
        
        # Update user's unread count
        await users_collection().update_one(
            {"_id": user_id_obj},
            {"$inc": {"unread_notifications": 1}}
        )
        
        return {
            "status": "created",
            "notification_id": str(result.inserted_id)
        }
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
        skip: int = 0,
        notification_type: str = None
    ) -> Dict[str, Any]:
        """
        Get notifications for a user.
        """
        query = {
            "user_id": ObjectId(user_id),
            "dismissed_at": None
        }
        
        if unread_only:
            query["read_at"] = None
        
        if notification_type:
            query["type"] = notification_type
        
        notifications = await notifications_collection().find(query).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(length=limit)
        
        # Convert ObjectIds
        for n in notifications:
            n["_id"] = str(n["_id"])
            n["user_id"] = str(n["user_id"])
        
        # Count totals
        total = await notifications_collection().count_documents(query)
        unread_count = await notifications_collection().count_documents({
            "user_id": ObjectId(user_id),
            "read_at": None,
            "dismissed_at": None
        })
        
        return {
            "notifications": notifications,
            "total": total,
            "unread_count": unread_count
        }
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        result = await notifications_collection().update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": ObjectId(user_id),
                "read_at": None
            },
            {
                "$set": {"read_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            await users_collection().update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"unread_notifications": -1}}
            )
            return True
        return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read."""
        result = await notifications_collection().update_many(
            {
                "user_id": ObjectId(user_id),
                "read_at": None,
                "dismissed_at": None
            },
            {
                "$set": {"read_at": datetime.utcnow()}
            }
        )
        
        await users_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"unread_notifications": 0}}
        )
        
        return result.modified_count
    
    async def dismiss_notification(self, notification_id: str, user_id: str) -> bool:
        """Dismiss a notification."""
        result = await notifications_collection().update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": ObjectId(user_id)
            },
            {
                "$set": {"dismissed_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            # Decrement unread if it was unread
            notification = await notifications_collection().find_one(
                {"_id": ObjectId(notification_id)}
            )
            if notification and not notification.get("read_at"):
                await users_collection().update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"unread_notifications": -1}}
                )
            return True
        return False
    
    async def click_notification(self, notification_id: str, user_id: str) -> bool:
        """Record notification click (for analytics)."""
        result = await notifications_collection().update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": ObjectId(user_id)
            },
            {
                "$set": {
                    "clicked_at": datetime.utcnow(),
                    "read_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    # ============ Settings Management ============
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get notification settings for a user."""
        settings = await notification_settings_collection().find_one(
            {"user_id": ObjectId(user_id)}
        )
        
        if settings:
            settings["_id"] = str(settings["_id"])
            settings["user_id"] = str(settings["user_id"])
            return settings.get("preferences", DEFAULT_SETTINGS)
        
        return DEFAULT_SETTINGS
    
    async def update_user_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update notification settings for a user."""
        await notification_settings_collection().update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$set": {
                    "preferences": settings,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return {"status": "updated", "settings": settings}
    
    def _should_notify(
        self,
        settings: Dict,
        notification_type: str,
        category: str
    ) -> bool:
        """Check if user should receive this notification type."""
        if notification_type == NotificationType.OPPORTUNITY_MATCH:
            opps = settings.get("opportunities", {})
            return opps.get("enabled", True)
        
        elif notification_type == NotificationType.DEADLINE_REMINDER:
            return settings.get("deadlines", {}).get("enabled", True)
        
        elif notification_type == NotificationType.LEARNING_REMINDER:
            return settings.get("learning", {}).get("enabled", True)
        
        elif notification_type == NotificationType.RECRUITER_ACTIVITY:
            return settings.get("recruiter_activity", {}).get("enabled", True)
        
        elif notification_type == NotificationType.ACHIEVEMENT:
            return settings.get("achievements", {}).get("enabled", True)
        
        return True
    
    # ============ Trigger Checks ============
    
    async def check_opportunity_matches(self):
        """
        Check for new high-scoring opportunity matches.
        Trigger: Score >= 75%
        """
        from .recommendation_engine import recommendation_engine
        
        # Get all students with notifications enabled
        students = await users_collection().find({
            "role": "student"
        }).to_list(length=500)
        
        notifications_created = 0
        
        for student in students:
            student_id = str(student["_id"])
            settings = await self.get_user_settings(student_id)
            
            if not settings.get("opportunities", {}).get("enabled", True):
                continue
            
            threshold = settings.get("opportunities", {}).get("min_score_threshold", 75)
            
            # Get top job recommendations
            result = await recommendation_engine.recommend_jobs(student_id, limit=5)
            
            for rec in result.get("recommendations", []):
                if rec["score"] >= threshold:
                    job = rec["job"]
                    
                    await self.create_notification(
                        user_id=student_id,
                        notification_type=NotificationType.OPPORTUNITY_MATCH,
                        category="job",
                        priority=NotificationPriority.HIGH if rec["score"] >= 85 else NotificationPriority.MEDIUM,
                        title=f"New match: {job.get('title', 'Job')}",
                        message=f"{job.get('company', 'Company')} - {rec['score']}% match",
                        action_url=f"/opportunities/jobs/{job.get('_id')}",
                        action_text="View Job",
                        related_entity={
                            "entity_type": "job",
                            "entity_id": job.get("_id"),
                            "entity_preview": {
                                "title": job.get("title"),
                                "company": job.get("company")
                            }
                        },
                        trigger_info={
                            "rule": "high_match_job",
                            "score": rec["score"],
                            "threshold": threshold
                        }
                    )
                    notifications_created += 1
        
        return {"notifications_created": notifications_created}
    
    async def check_deadline_reminders(self):
        """
        Check for approaching deadlines.
        Trigger: Apply-by date within 3 days
        """
        cutoff = datetime.utcnow() + timedelta(days=3)
        now = datetime.utcnow()
        
        # Find jobs expiring soon
        expiring_jobs = await opportunities_jobs_collection().find({
            "apply_by": {"$gte": now, "$lte": cutoff},
            "is_active": True
        }).to_list(length=100)
        
        notifications_created = 0
        
        for job in expiring_jobs:
            # Find students who saved/clicked this job
            from .recommendation_engine import recommendation_feedback_collection
            
            interactions = await recommendation_feedback_collection().find({
                "opportunity_id": job["_id"],
                "opportunity_type": "job",
                "action": {"$in": ["clicked", "saved"]}
            }).to_list(length=100)
            
            for interaction in interactions:
                student_id = str(interaction["student_id"])
                days_left = (job["apply_by"] - now).days
                
                await self.create_notification(
                    user_id=student_id,
                    notification_type=NotificationType.DEADLINE_REMINDER,
                    category="job",
                    priority=NotificationPriority.URGENT if days_left <= 1 else NotificationPriority.HIGH,
                    title="Application deadline approaching",
                    message=f"{job.get('title')} at {job.get('company')} closes in {days_left} days",
                    action_url=f"/opportunities/jobs/{job.get('_id')}",
                    action_text="Apply Now",
                    related_entity={
                        "entity_type": "job",
                        "entity_id": str(job["_id"]),
                        "days_until_deadline": days_left
                    },
                    trigger_info={
                        "rule": "deadline_approaching",
                        "days_remaining": days_left
                    }
                )
                notifications_created += 1
        
        return {"notifications_created": notifications_created}
    
    async def check_learning_reminders(self):
        """
        Check for inactive learning paths.
        Trigger: Path inactive for 7+ days
        """
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Find inactive learning paths
        inactive_paths = await learning_paths_collection().find({
            "progress.updated_at": {"$lt": cutoff},
            "progress.completion_percentage": {"$lt": 100}
        }).to_list(length=200)
        
        notifications_created = 0
        
        for path in inactive_paths:
            student_id = str(path["student_id"])
            skill = path.get("skill", "your skill")
            days_inactive = (datetime.utcnow() - path["progress"]["updated_at"]).days
            
            await self.create_notification(
                user_id=student_id,
                notification_type=NotificationType.LEARNING_REMINDER,
                category="learning",
                priority=NotificationPriority.MEDIUM,
                title="Continue your learning path",
                message=f"Your {skill} learning has been inactive for {days_inactive} days",
                action_url=f"/learning/paths/{path.get('_id')}",
                action_text="Resume Learning",
                related_entity={
                    "entity_type": "learning_path",
                    "entity_id": str(path["_id"]),
                    "skill": skill,
                    "completion": path["progress"]["completion_percentage"]
                },
                trigger_info={
                    "rule": "inactive_learning_path",
                    "days_inactive": days_inactive
                }
            )
            notifications_created += 1
        
        return {"notifications_created": notifications_created}
    
    async def check_achievements(self):
        """
        Check for AI profile improvements.
        Trigger: Score increased by 10+ points
        """
        # This would need historical score tracking
        # For now, return placeholder
        return {"notifications_created": 0, "note": "Needs score history tracking"}
    
    async def create_recruiter_notification(
        self,
        student_id: str,
        activity_type: str,
        recruiter_name: str,
        details: Dict = None
    ):
        """
        Create notification for recruiter activity.
        Called by other services when recruiter takes action.
        """
        titles = {
            "profile_view": f"{recruiter_name} viewed your profile",
            "interview": f"Interview scheduled by {recruiter_name}",
            "message": f"New message from {recruiter_name}",
            "offer": f"Offer received from {recruiter_name}!"
        }
        
        priorities = {
            "profile_view": NotificationPriority.LOW,
            "interview": NotificationPriority.HIGH,
            "message": NotificationPriority.MEDIUM,
            "offer": NotificationPriority.URGENT
        }
        
        return await self.create_notification(
            user_id=student_id,
            notification_type=NotificationType.RECRUITER_ACTIVITY,
            category=activity_type,
            priority=priorities.get(activity_type, NotificationPriority.MEDIUM),
            title=titles.get(activity_type, f"Activity from {recruiter_name}"),
            message=details.get("message", ""),
            action_url=details.get("action_url"),
            action_text=details.get("action_text", "View"),
            related_entity=details.get("entity"),
            trigger_info={"rule": f"recruiter_{activity_type}"}
        )
    
    async def create_achievement_notification(
        self,
        student_id: str,
        achievement_type: str,
        details: Dict = None
    ):
        """
        Create notification for achievements.
        Called by other services when student achieves something.
        """
        return await self.create_notification(
            user_id=student_id,
            notification_type=NotificationType.ACHIEVEMENT,
            category=achievement_type,
            priority=NotificationPriority.LOW,
            title=details.get("title", "🎉 Achievement unlocked!"),
            message=details.get("message", ""),
            action_url=details.get("action_url"),
            action_text=details.get("action_text", "View"),
            trigger_info={"rule": f"achievement_{achievement_type}"}
        )
    
    # ============ Batching Logic ============
    
    async def batch_pending_notifications(self, user_id: str):
        """
        Batch similar pending notifications to prevent spam.
        Groups notifications of same type created in last hour.
        """
        cutoff = datetime.utcnow() - timedelta(hours=1)
        
        # Get recent unread notifications
        notifications = await notifications_collection().find({
            "user_id": ObjectId(user_id),
            "read_at": None,
            "created_at": {"$gte": cutoff}
        }).to_list(length=50)
        
        # Group by type
        groups = {}
        for n in notifications:
            ntype = n.get("type")
            if ntype not in groups:
                groups[ntype] = []
            groups[ntype].append(n)
        
        batched = 0
        
        for ntype, notifs in groups.items():
            if len(notifs) > self.batch_threshold:
                # Create batch notification
                await self.create_notification(
                    user_id=user_id,
                    notification_type=NotificationType.BATCH,
                    category=ntype,
                    priority=NotificationPriority.MEDIUM,
                    title=f"{len(notifs)} new {ntype} notifications",
                    message="View all in your notification center",
                    action_url="/notifications",
                    trigger_info={"rule": "batch", "count": len(notifs)}
                )
                
                # Mark individual ones as batched
                for n in notifs:
                    await notifications_collection().update_one(
                        {"_id": n["_id"]},
                        {"$set": {"batched": True, "batch_created_at": datetime.utcnow()}}
                    )
                    batched += 1
        
        return {"batched_count": batched}
    
    # ============ Analytics ============
    
    async def get_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """Get notification statistics for a user."""
        total = await notifications_collection().count_documents({
            "user_id": ObjectId(user_id)
        })
        
        unread = await notifications_collection().count_documents({
            "user_id": ObjectId(user_id),
            "read_at": None,
            "dismissed_at": None
        })
        
        clicked = await notifications_collection().count_documents({
            "user_id": ObjectId(user_id),
            "clicked_at": {"$ne": None}
        })
        
        dismissed = await notifications_collection().count_documents({
            "user_id": ObjectId(user_id),
            "dismissed_at": {"$ne": None}
        })
        
        # By type
        by_type = {}
        for ntype in NotificationType:
            count = await notifications_collection().count_documents({
                "user_id": ObjectId(user_id),
                "type": ntype.value
            })
            if count > 0:
                by_type[ntype.value] = count
        
        return {
            "total": total,
            "unread": unread,
            "clicked": clicked,
            "dismissed": dismissed,
            "click_rate": round(clicked / total * 100, 1) if total > 0 else 0,
            "by_type": by_type
        }
    
    # ============ Run All Checks ============
    
    async def run_all_checks(self):
        """
        Run all notification trigger checks.
        Called by background scheduler.
        """
        results = {
            "opportunity_matches": await self.check_opportunity_matches(),
            "deadline_reminders": await self.check_deadline_reminders(),
            "learning_reminders": await self.check_learning_reminders(),
            "achievements": await self.check_achievements(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return results


# Singleton instance
notification_service = NotificationService()
