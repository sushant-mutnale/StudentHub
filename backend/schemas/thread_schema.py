from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ThreadParticipant(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    role: Optional[str] = None


class ThreadSummary(BaseModel):
    id: str
    participants: List[ThreadParticipant]
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class ThreadListResponse(BaseModel):
    threads: List[ThreadSummary]


class ThreadCreateRequest(BaseModel):
    participant_ids: Optional[List[str]] = None
    participant_usernames: Optional[List[str]] = None
    initial_message: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_participants(self):
        ids = self.participant_ids or []
        usernames = self.participant_usernames or []
        if not ids and not usernames:
            raise ValueError("Provide at least one participant id or username.")
        return self


class ThreadMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ThreadMessage(BaseModel):
    id: str
    thread_id: str
    sender_id: str
    text: str
    created_at: datetime
    read_by: List[str]


class ThreadDetailResponse(BaseModel):
    thread: ThreadSummary
    messages: List[ThreadMessage]
    has_more: bool



