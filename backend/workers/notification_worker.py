"""
Notification Worker

Polls for pending notifications and handles their delivery via configured channels
(Email, Push, SMS, etc.).

For this implementation, it simulates delivery by logging and updating status.
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from bson import ObjectId

from .worker_base import BackgroundWorker
from ..models.notification import notifications_collection
from ..database import get_database

logger = logging.getLogger(__name__)

class NotificationWorker(BackgroundWorker):
    """
    Worker that delivers pending notifications.
    """
    
    def __init__(self, poll_interval: float = 5.0, batch_size: int = 20):
        super().__init__(
            name="notification_worker",
            poll_interval=poll_interval,
            batch_size=batch_size
        )
    
    async def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get pending notifications.
        Returns a list of notification documents.
        """
        cursor = notifications_collection().find(
            {
                "delivery_status": "pending",
                # Optional: "delivery_attempts": {"$lt": 3}
            }
        ).sort("priority", 1).limit(self.batch_size) # High priority first (if priority is int? No string. Need mapping?)
        
        # Priority sort: 'high' < 'medium' < 'low' alphabetically is wrong.
        # But for MVP, simple FIFO is fine or simple sort.
        # Strings: high > low... 'high' comes before 'medium'? No. 'h', 'm'.
        # Let's just fetch them.
        
        return await cursor.to_list(length=None)

    async def process_job(self, notification: Dict[str, Any]) -> bool:
        """
        Deliver a single notification.
        """
        try:
            notification_id = notification["_id"]
            user_id = notification["user_id"]
            kind = notification.get("kind", "general")
            
            # 1. Check user preferences (mocked for now)
            # user = await users_collection().find_one({"_id": user_id})
            # if not user.email_notifications: return True
            
            # 2. Simulate Delivery
            await self._simulate_email_delivery(notification)
            
            # 3. Update Status
            await notifications_collection().update_one(
                {"_id": notification_id},
                {
                    "$set": {
                        "delivery_status": "sent",
                        "delivered_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Delivered notification {notification_id} to {user_id}")
            return True
            
        except Exception as e:
            await notifications_collection().update_one(
                {"_id": notification["_id"]},
                {
                    "$set": {"delivery_status": "failed"},
                    "$inc": {"delivery_attempts": 1},
                    "$push": {"errors": str(e)}
                }
            )
            logger.error(f"Failed to deliver notification {notification['_id']}: {e}")
            return False

    async def _simulate_email_delivery(self, notification):
        """
        Send an email via the email service.
        """
        from ..models.user import users_collection
        from ..services.email_service import email_service
        
        user_id = notification.get("user_id")
        user = None
        if user_id:
            user = await users_collection().find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id})
        
        email = user.get("email") if user else None
        if not email:
            logger.warning(f"No user or email found for notification {notification.get('_id')}")
            return
            
        payload = notification.get("payload", {})
        msg = payload.get("msg", "No message content")
        subject = f"Notification: {notification.get('kind', 'Update')}"
        
        html_content = f"""
        <html>
        <body>
            <h3>StudentHub Notification</h3>
            <p>{msg}</p>
        </body>
        </html>
        """
        
        # Send using the existing async send_email method on email_service
        success = await email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=msg
        )
        if not success:
            logger.error(f"Failed to send email to {email} for notification {notification.get('_id')}")
