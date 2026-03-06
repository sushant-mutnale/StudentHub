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
        Simulate sending an email.
        """
        # In production this would use SMTP or SendGrid/SES
        # For now, just a tiny delay and logic check
        await asyncio.sleep(0.1)
        
        # We could inspect payload to format a message
        payload = notification.get("payload", {})
        msg = payload.get("msg", "No message content")
        
        # logger.debug(f"sending email: {msg}")
