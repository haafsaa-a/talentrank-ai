import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api import routes as api_routes
from auth import linkedin_oauth
from job_queue.job_queue import worker, recover_pending_jobs
from ingestion.sheets_poller import poll_sheets
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the job queue worker
    worker_task = asyncio.create_task(worker())
    
    # Recover jobs on startup
    await recover_pending_jobs()

    # Start the Google Sheets poller scheduler
    scheduler.add_job(poll_sheets, 'interval', minutes=5)
    scheduler.start()
    logger.info("Scheduler started.")

    yield

    # Shutdown
    worker_task.cancel()
    scheduler.shutdown()
    logger.info("Shutting down...")

app = FastAPI(title="TalentRank AI", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin for origin in [
            "http://localhost:5173",
            "https://talentrank-frontend.onrender.com",
            settings.APP_FRONTEND_URL,
        ] if origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_routes.router, prefix="/api", tags=["API"])
app.include_router(linkedin_oauth.router, prefix="/auth/linkedin", tags=["OAuth"])

@app.get("/")
def read_root():
    return {"message": "Welcome to TalentRank AI Backend"}
