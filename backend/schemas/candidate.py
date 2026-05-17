from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional
from uuid import UUID
from datetime import datetime
from models.candidate import CandidateStatus

class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

class CandidateResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_connected: bool
    status: CandidateStatus
    created_at: datetime

    class Config:
        from_attributes = True
