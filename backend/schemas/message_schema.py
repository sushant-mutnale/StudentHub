from datetime import datetime

from pydantic import BaseModel

from .base import MongoModel


class MessageCreate(MongoModel):
    receiver_id: str
    content: str


class MessageResponse(BaseModel):
    """Public message response model with string IDs (Pydantic v2 compatible)."""
    id: str
    sender_id: str
    receiver_id: str
    content: str
    created_at: datetime
    read: bool

    class Config:
        from_attributes = True


