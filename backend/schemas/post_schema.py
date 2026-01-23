from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .base import MongoModel


class CommentSchema(BaseModel):
    """Public comment response model with string IDs (Pydantic v2 compatible)."""
    id: str
    user_id: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostBase(MongoModel):
    content: str
    tags: List[str] = Field(default_factory=list)


class PostCreate(PostBase):
    pass


class PostUpdate(MongoModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class CommentCreate(MongoModel):
    text: str


class PostResponse(BaseModel):
    """Public post response model with string IDs (Pydantic v2 compatible)."""
    id: str
    author_id: str
    author_name: str
    author_username: str
    author_role: str
    author_avatar_url: Optional[str] = None
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    likes: List[str] = Field(default_factory=list)
    comments: List[CommentSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True

