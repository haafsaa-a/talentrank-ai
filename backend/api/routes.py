from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import uuid
from sqlalchemy import cast, Text

from database import get_db
from models.candidate import Candidate, CandidateStatus
from models.profile import Profile
from schemas.candidate import CandidateCreate, CandidateResponse
from schemas.profile import CandidateDetailResponse

router = APIRouter()

@router.get("/candidates", response_model=List[CandidateDetailResponse])
async def list_candidates(
    status: Optional[CandidateStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Candidate).options(selectinload(Candidate.profile)).order_by(desc(Candidate.created_at))
    if status:
        stmt = stmt.where(Candidate.status == status)
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    return candidates

@router.get("/candidates/search", response_model=List[CandidateDetailResponse])
async def search_candidates(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Candidate).options(selectinload(Candidate.profile)).where(
        or_(
            Candidate.name.ilike(f"%{q}%"),
            Candidate.email.ilike(f"%{q}%")
        )
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    return candidates

@router.get("/candidates/filter", response_model=List[CandidateDetailResponse])
async def filter_candidates(
    skill: Optional[str] = None,
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Candidate).join(Profile).options(selectinload(Candidate.profile))
    if skill:
        stmt = stmt.where(cast(Profile.skills, Text).ilike(f"%{skill}%"))
    if domain:
        stmt = stmt.where(cast(Profile.domain_tags, Text).ilike(f"%{domain}%"))
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    return candidates

@router.get("/candidates/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Candidate).options(selectinload(Candidate.profile)).where(Candidate.id == candidate_id)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Delete profile first (foreign key constraint)
    profile_stmt = select(Profile).where(Profile.candidate_id == candidate_id)
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalar_one_or_none()
    if profile:
        await db.delete(profile)

    # Delete candidate
    candidate_stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate_result = await db.execute(candidate_stmt)
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await db.delete(candidate)
    await db.commit()
    return {"message": "Candidate deleted successfully"}

@router.post("/candidates", response_model=CandidateResponse)
async def create_candidate(candidate_in: CandidateCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Candidate).where(Candidate.email == candidate_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    candidate = Candidate(
        name=candidate_in.name,
        email=candidate_in.email,
        github_url=candidate_in.github_url,
        portfolio_url=candidate_in.portfolio_url,
        status=CandidateStatus.linkedin_pending
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_stmt = select(Candidate)
    total_res = await db.execute(total_stmt)
    total = len(total_res.scalars().all())

    done_stmt = select(Candidate).where(Candidate.status == CandidateStatus.done)
    done_res = await db.execute(done_stmt)
    done = len(done_res.scalars().all())

    pending = total - done

    return {
        "total": total,
        "done": done,
        "pending": pending,
        "top_domains": []
    }

@router.get("/mock/candidates")
async def get_mock_candidates():
    return [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Alice Developer",
            "email": "alice@example.com",
            "github_url": "https://github.com/alice",
            "portfolio_url": "https://alice.dev",
            "linkedin_connected": True,
            "status": "done",
            "profile": {
                "summary": "Alice is a highly skilled frontend developer with a strong eye for design.",
                "skills": ["React", "TypeScript", "TailwindCSS"],
                "top_projects": [{"name": "E-commerce UI", "description": "A beautiful storefront", "stars": 120}],
                "experience_years": 4,
                "domain_tags": ["Frontend", "Design"]
            }
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Bob Backend",
            "email": "bob@example.com",
            "github_url": "https://github.com/bob",
            "portfolio_url": None,
            "linkedin_connected": True,
            "status": "done",
            "profile": {
                "summary": "Bob excels in building scalable backend systems and APIs using Python and Go.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "top_projects": [{"name": "Microservices Demo", "description": "Go microservices", "stars": 45}],
                "experience_years": 6,
                "domain_tags": ["Backend", "DevOps"]
            }
        }
    ]