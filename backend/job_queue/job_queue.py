import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models.candidate import Candidate, CandidateStatus
from scrapers.github_scraper import scrape_github
from scrapers.portfolio_scraper import scrape_portfolio
from ai.profile_generator import generate_profile

logger = logging.getLogger(__name__)

# In-memory asyncio queue
scrape_queue = asyncio.Queue()

async def worker():
    """Background worker to process items from the queue."""
    logger.info("Job queue worker started.")
    while True:
        candidate_id = await scrape_queue.get()
        try:
            await process_candidate(candidate_id)
        except Exception as e:
            logger.error(f"Error processing candidate {candidate_id}: {e}")
            async with AsyncSessionLocal() as session:
                candidate = await session.get(Candidate, candidate_id)
                if candidate:
                    candidate.status = CandidateStatus.failed
                    await session.commit()
        finally:
            scrape_queue.task_done()

async def process_candidate(candidate_id: str):
    """Processes a single candidate: scrapes data and generates AI profile."""
    async with AsyncSessionLocal() as session:
        candidate = await session.get(Candidate, candidate_id)
        if not candidate:
            logger.warning(f"Candidate {candidate_id} not found in DB.")
            return

        # 1. Get CV text from candidate record
        cv_text = candidate.cv_text or ""

        # 2. Scrape GitHub and Portfolio concurrently
        github_task = scrape_github(candidate.github_url) if candidate.github_url else asyncio.sleep(0, result=None)
        portfolio_task = scrape_portfolio(candidate.portfolio_url) if candidate.portfolio_url else asyncio.sleep(0, result="")

        github_data, portfolio_text = await asyncio.gather(github_task, portfolio_task)

        # 3. Get LinkedIn data from existing profile record
        from models.profile import Profile
        stmt = select(Profile).where(Profile.candidate_id == candidate_id)
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        raw_linkedin = {}
        if profile:
            raw_linkedin = profile.raw_linkedin_data or {}

        # 4. Call AI to generate and save profile
        try:
            ai_data = await generate_profile(
                candidate_id=str(candidate_id),
                github_data=github_data or {},
                portfolio_text=portfolio_text or "",
                linkedin_data=raw_linkedin or {},
                cv_text=cv_text,
                db_session=AsyncSessionLocal
            )
            candidate.status = CandidateStatus.done
            await session.commit()
            logger.info(f"Successfully processed candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Failed to generate AI profile for {candidate_id}: {e}")
            candidate.status = CandidateStatus.failed
            await session.commit()

async def recover_pending_jobs():
    """Recover pending jobs on startup by re-enqueueing candidates with pending/scraping status."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                from sqlalchemy import select, or_
                from models.candidate import Candidate, CandidateStatus
                stmt = select(Candidate).where(
                    or_(
                        Candidate.status == CandidateStatus.scraping,
                        Candidate.status == CandidateStatus.pending
                    )
                )
                result = await session.execute(stmt)
                candidates = result.scalars().all()
                for candidate in candidates:
                    await scrape_queue.put(str(candidate.id))
                    logger.info(f"Re-enqueued candidate {candidate.id} for scraping.")
    except Exception as e:
        logger.warning(f"Could not recover pending jobs: {e}")