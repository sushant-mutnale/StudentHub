from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel
from .base import MongoModel

class NotificationResponse(MongoModel):
    id: str
    kind: str
    payload: Dict[str, Any]
    is_read: bool
    read_at: Optional[datetime] = None
    priority: str
    category: str
    created_at: datetime
