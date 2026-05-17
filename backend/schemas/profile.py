from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class Project(BaseModel):
    name: str
    description: Optional[str] = None
    stars: int

class ProfileResponse(BaseModel):
    id: Optional[UUID] = None
    candidate_id: Optional[UUID] = None
    summary: Optional[str] = None
    skills: Optional[list] = None
    top_projects: Optional[list] = None
    experience_years: Optional[int] = None
    domain_tags: Optional[list] = None
    talent_rank_score: Optional[float] = None
    raw_github_data: Optional[dict] = None
    raw_portfolio_text: Optional[str] = None
    raw_linkedin_data: Optional[dict] = None
    generated_at: Optional[datetime] = None
    cv_skills: Optional[list] = None
    cv_experience: Optional[list] = None
    cv_education: Optional[list] = None
    raw_cv_text: Optional[str] = None

    class Config:
        from_attributes = True

class CandidateDetailResponse(BaseModel):
    # Combines Candidate and Profile for the frontend detailed view
    id: UUID
    name: str
    email: str
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_connected: bool
    status: str
    profile: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
