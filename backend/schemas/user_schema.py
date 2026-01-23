from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, EmailStr, Field

from .base import MongoModel


class UserBase(MongoModel):
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)


class StudentCreate(UserBase):
    full_name: str
    password: str
    prn: str
    college: str
    branch: str
    year: str
    role: str = "student"


class RecruiterCreate(UserBase):
    password: str
    company_name: str
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None
    role: str = "recruiter"


class UserLogin(MongoModel):
    username: str
    password: str
    role: str


class UserPublic(BaseModel):
    """Public user response model with string IDs (Pydantic v2 compatible)."""
    id: str
    role: Literal["student", "recruiter"]
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    prn: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[str] = None
    company_name: Optional[str] = None
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(MongoModel):
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    full_name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[str] = None
    prn: Optional[str] = None
    company_name: Optional[str] = None
    contact_number: Optional[str] = None
    website: Optional[str] = None
    company_description: Optional[str] = None


