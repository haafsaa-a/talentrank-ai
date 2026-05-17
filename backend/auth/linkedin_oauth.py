import uuid
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.candidate import Candidate, CandidateStatus
from models.profile import Profile
from config import settings
from scrapers.linkedin_api import fetch_linkedin_profile
from job_queue.job_queue import scrape_queue
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Encryption setup for access tokens
fernet = Fernet(settings.ENCRYPTION_KEY.encode())

@router.get("/start")
async def start_linkedin_auth(email: str, db: AsyncSession = Depends(get_db)):
    """
    Step 1: Generate state and redirect to LinkedIn OAuth page.
    """
    stmt = select(Candidate).where(Candidate.email == email)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Generate state to prevent CSRF
    state_token = str(uuid.uuid4())
    candidate.state_token = state_token
    await db.commit()

    # Build Authorization URL
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={settings.LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
        f"&state={state_token}"
        f"&scope=openid%20profile%20email"
    )

    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def linkedin_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Step 2: Handle callback, exchange code for token, fetch profile, enqueue.
    """
    # 1. Validate state
    stmt = select(Candidate).where(Candidate.state_token == state)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid state token or candidate not found")

    # 2. Exchange code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            logger.error(f"Failed to get LinkedIn token: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to authenticate with LinkedIn")
        
        token_data = response.json()
        access_token = token_data.get("access_token")

    # 3. Store encrypted access token
    encrypted_token = fernet.encrypt(access_token.encode()).decode()
    candidate.linkedin_access_token = encrypted_token
    candidate.linkedin_connected = True
    
    # Clear state token
    candidate.state_token = None

    # 4. Fetch LinkedIn Profile
    raw_linkedin_data = await fetch_linkedin_profile(access_token)

    # 5. Store LinkedIn Data in Profile model
    stmt = select(Profile).where(Profile.candidate_id == candidate.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = Profile(candidate_id=candidate.id)
        db.add(profile)
    
    profile.raw_linkedin_data = raw_linkedin_data
    
    # 6. Update Status and Enqueue for scraping
    candidate.status = CandidateStatus.scraping
    await db.commit()
    
    await scrape_queue.put(candidate.id)

    # 7. Redirect to frontend success page
    return RedirectResponse(url=f"{settings.APP_FRONTEND_URL}/linkedin-success")
