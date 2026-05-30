import os
import json
import logging
import smtplib
import re
from email.message import EmailMessage
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from database import AsyncSessionLocal
from models.candidate import Candidate, CandidateStatus
from config import settings
import httpx
from models.profile import Profile  # noqa: F401 - needed to resolve SQLAlchemy relationships

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def get_credentials(scopes):
    """Returns Google credentials from either JSON string or file path."""
    creds_value = settings.GOOGLE_SHEETS_CREDENTIALS
    if not creds_value:
        logger.warning("GOOGLE_SHEETS_CREDENTIALS is not set.")
        return None
    try:
        if creds_value.strip().startswith("{"):
            creds_info = json.loads(creds_value)
            return Credentials.from_service_account_info(creds_info, scopes=scopes)
        else:
            if not os.path.exists(creds_value):
                logger.warning(f"Credentials file not found at: {creds_value}")
                return None
            return Credentials.from_service_account_file(creds_value, scopes=scopes)
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return None


def get_sheets_service():
    creds = get_credentials(SCOPES)
    if not creds:
        logger.warning("Google Sheets credentials not found. Aborting poll.")
        return None
    try:
        service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets service initialized successfully.")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets service: {e}")
        return None


async def download_cv_from_drive(drive_url: str, creds) -> bytes:
    if not drive_url:
        logger.warning("No Drive URL provided for CV download.")
        return None

    try:
        match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_url)
        if not match:
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
        if not match:
            logger.warning(f"Could not extract file ID from Drive URL: {drive_url}")
            return None

        file_id = match.group(1)
        download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

        import google.auth.transport.requests
        request = google.auth.transport.requests.Request()
        creds.refresh(request)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {creds.token}"},
                timeout=30
            )
            if response.status_code == 200:
                logger.info(f"CV downloaded successfully for file ID: {file_id}")
                return response.content
            elif response.status_code == 403:
                logger.error(f"CV download forbidden (403) for file {file_id}.")
                return None
            elif response.status_code == 404:
                logger.error(f"CV file not found (404) for file {file_id}.")
                return None
            else:
                logger.warning(f"CV download failed with status {response.status_code} for file {file_id}.")
                return None

    except httpx.TimeoutException:
        logger.error(f"CV download timed out for URL: {drive_url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading CV from {drive_url}: {e}")
        return None


async def process_cv(candidate_email: str, cv_url: str):
    if not cv_url:
        logger.warning(f"No CV URL provided for {candidate_email}. Skipping CV processing.")
        return

    try:
        from scrapers.cv_parser import parse_cv
        from sqlalchemy import select

        creds_for_drive = get_credentials(['https://www.googleapis.com/auth/drive.readonly'])
        if not creds_for_drive:
            logger.error("Could not load Drive credentials for CV download.")
            return

        pdf_bytes = await download_cv_from_drive(cv_url, creds_for_drive)

        if not pdf_bytes:
            logger.warning(f"CV download returned no data for {candidate_email}. Skipping CV parsing.")
            return

        cv_result = await parse_cv(pdf_bytes)

        if not cv_result:
            logger.warning(f"CV parser returned no result for {candidate_email}.")
            return

        cv_text = cv_result.get("cv_text", "").strip()

        if not cv_text:
            logger.warning(f"CV parsed but extracted text is empty for {candidate_email}.")
            return

        async with AsyncSessionLocal() as db:
            stmt = select(Candidate).where(Candidate.email == candidate_email)
            res = await db.execute(stmt)
            cand = res.scalar_one_or_none()

            if cand:
                cand.cv_text = cv_text
                await db.commit()
                logger.info(f"CV parsed and saved successfully for {candidate_email}.")
            else:
                logger.error(f"Candidate {candidate_email} not found in DB when saving CV text.")

    except ImportError:
        logger.error("cv_parser module not found. Make sure scrapers/cv_parser.py exists.")
    except Exception as e:
        logger.error(f"CV processing failed for {candidate_email}: {e}")


def send_followup_email(candidate_email: str, candidate_name: str):
    if not settings.RESEND_API_KEY:
        logger.warning(f"Resend API key not configured. Skipping email to {candidate_email}.")
        return

    link = f"{settings.APP_BACKEND_URL}/auth/linkedin/start?email={candidate_email}"

    import json as json_lib
    import asyncio

    payload = {
        "from": "TalentRank <noreply@talentrank.online>",
        "to": [candidate_email],
        "subject": "Next Step: Connect your LinkedIn Profile",
        "text": f"Hi {candidate_name},\n\nThank you for applying! Please connect your LinkedIn profile so our AI can review your application:\n{link}\n\nThanks,\nThe TalentRank Team"
    }

    async def _send():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; TalentRank/1.0)"
                },
                json=payload,
                timeout=30
            )
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Email sent successfully to {candidate_email}.")
            else:
                logger.error(f"Resend error {response.status_code} for {candidate_email}: {response.text}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_send())
        else:
            loop.run_until_complete(_send())
    except Exception as e:
        logger.error(f"Failed to send email to {candidate_email}: {e}")
        

async def poll_sheets():
    logger.info("Starting Google Sheets poll...")

    service = get_sheets_service()
    if not service:
        logger.error("Sheets service unavailable. Aborting poll.")
        return

    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range="Sheet1!A:F"
        ).execute()
        values = result.get('values', [])

        if not values or len(values) <= 1:
            logger.info("No data found in sheet or only header row present.")
            return

        logger.info(f"Found {len(values) - 1} row(s) in sheet (excluding header).")

        success_count = 0
        duplicate_count = 0
        error_count = 0

        for i, row in enumerate(values[1:], start=2):

            if len(row) < 3:
                logger.warning(f"Row {i}: Skipped — insufficient columns. Got {len(row)}. Row data: {row}")
                error_count += 1
                continue

            name = row[1].strip() if row[1] else ""
            email = row[2].strip() if row[2] else ""

            if not name:
                logger.warning(f"Row {i}: Skipped — name field is empty.")
                error_count += 1
                continue

            if not email:
                logger.warning(f"Row {i}: Skipped — email field is empty.")
                error_count += 1
                continue

            if not is_valid_email(email):
                logger.warning(f"Row {i}: Skipped — invalid email format: '{email}'.")
                error_count += 1
                continue

            github_url = row[3].strip() if len(row) > 3 and row[3] else None
            portfolio_url = row[4].strip() if len(row) > 4 and row[4] else None
            cv_url = row[5].strip() if len(row) > 5 and row[5] else None

            try:
                from sqlalchemy import select

                async with AsyncSessionLocal() as db:
                    stmt = select(Candidate).where(Candidate.email == email)
                    res = await db.execute(stmt)
                    existing = res.scalar_one_or_none()

                    if existing:
                        existing.name = name
                        existing.github_url = github_url or existing.github_url
                        existing.portfolio_url = portfolio_url or existing.portfolio_url

                        if cv_url and existing.cv_url != cv_url:
                            existing.cv_url = cv_url

                        await db.commit()
                        duplicate_count += 1
                        logger.info(f"Row {i}: Duplicate entry for '{email}'. Profile updated.")

                        if cv_url and not existing.cv_text:
                            await process_cv(email, cv_url)

                    else:
                        new_cand = Candidate(
                            name=name,
                            email=email,
                            github_url=github_url,
                            portfolio_url=portfolio_url,
                            cv_url=cv_url,
                            status=CandidateStatus.linkedin_pending,
                            created_at=datetime.utcnow()
                        )
                        db.add(new_cand)
                        await db.commit()
                        success_count += 1
                        logger.info(f"Row {i}: New candidate '{name}' ({email}) stored successfully.")

                        send_followup_email(email, name)

                        if cv_url:
                            await process_cv(email, cv_url)

            except Exception as e:
                logger.error(f"Row {i}: Database error while processing '{email}': {e}")
                error_count += 1
                continue

        logger.info(
            f"Poll complete — "
            f"{success_count} new candidate(s) added, "
            f"{duplicate_count} duplicate(s) updated, "
            f"{error_count} row(s) skipped due to errors."
        )

    except Exception as e:
        logger.error(f"Critical error during sheet polling: {e}")