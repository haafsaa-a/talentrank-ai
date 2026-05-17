import os
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
    """TC-03: Validates email format before processing."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def get_sheets_service():
    if not os.path.exists(settings.GOOGLE_SHEETS_CREDENTIALS):
        logger.warning("Google Sheets credentials not found. Aborting poll.")
        return None
    try:
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets service initialized successfully.")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets service: {e}")
        return None


async def download_cv_from_drive(drive_url: str, creds) -> bytes:
    """Downloads CV PDF from Google Drive using service account credentials."""
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
                logger.error(f"CV download forbidden (403) for file {file_id}. Check Drive sharing permissions.")
                return None
            elif response.status_code == 404:
                logger.error(f"CV file not found (404) for file {file_id}. File may have been deleted.")
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
    """Downloads, parses and saves CV text for a candidate."""
    if not cv_url:
        logger.warning(f"No CV URL provided for {candidate_email}. Skipping CV processing.")
        return

    try:
        from scrapers.cv_parser import parse_cv
        from sqlalchemy import select

        creds_for_drive = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

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
                logger.info(f"CV parsed and saved successfully for {candidate_email}. "
                            f"Extracted {len(cv_text)} characters.")
            else:
                logger.error(f"Candidate {candidate_email} not found in DB when saving CV text.")

    except ImportError:
        logger.error("cv_parser module not found. Make sure scrapers/cv_parser.py exists.")
    except Exception as e:
        logger.error(f"CV processing failed for {candidate_email}: {e}")


def send_followup_email(candidate_email: str, candidate_name: str):
    if not settings.SMTP_PASSWORD:
        logger.warning(f"SMTP not configured. Skipping email to {candidate_email}.")
        return

    link = f"http://localhost:8000/auth/linkedin/start?email={candidate_email}"
    msg = EmailMessage()
    msg.set_content(f"""
Hi {candidate_name},

Thank you for applying! Please connect your LinkedIn profile so our AI can review your application:
{link}

Thanks,
The TalentRank Team
""")
    msg['Subject'] = 'Next Step: Connect your LinkedIn Profile'
    msg['From'] = settings.SMTP_USER
    msg['To'] = candidate_email

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Follow-up email sent successfully to {candidate_email}.")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in config.")
    except smtplib.SMTPConnectError:
        logger.error(f"Could not connect to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT}.")
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"Email address refused by SMTP server: {candidate_email}.")
    except Exception as e:
        logger.error(f"Failed to send email to {candidate_email}: {e}")


async def poll_sheets():
    """Polls Google Sheets and ingests new rows."""

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

            # TC-02: Skip rows missing required fields
            if len(row) < 3:
                logger.warning(f"Row {i}: Skipped — insufficient columns. "
                               f"Expected at least 3, got {len(row)}. Row data: {row}")
                error_count += 1
                continue

            name = row[1].strip() if row[1] else ""
            email = row[2].strip() if row[2] else ""

            # TC-02: Validate name not empty
            if not name:
                logger.warning(f"Row {i}: Skipped — name field is empty.")
                error_count += 1
                continue

            # TC-02: Validate email not empty
            if not email:
                logger.warning(f"Row {i}: Skipped — email field is empty.")
                error_count += 1
                continue

            # TC-03: Validate email format
            if not is_valid_email(email):
                logger.warning(f"Row {i}: Skipped — invalid email format: '{email}'. "
                               f"Please enter a valid email address.")
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
                        # TC-04: Duplicate detected — update existing record
                        existing.name = name
                        existing.github_url = github_url or existing.github_url
                        existing.portfolio_url = portfolio_url or existing.portfolio_url

                        # Update cv_url only if a new one is provided
                        if cv_url and existing.cv_url != cv_url:
                            existing.cv_url = cv_url

                        await db.commit()
                        duplicate_count += 1
                        logger.info(
                            f"Row {i}: Duplicate entry detected for '{email}'. "
                            f"Profile updated with latest submission at {datetime.utcnow().isoformat()}Z."
                        )

                        # Re-process CV if new URL provided but no text yet
                        if cv_url and not existing.cv_text:
                            await process_cv(email, cv_url)

                    else:
                        # TC-01: New candidate — insert with timestamp
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
                        logger.info(
                            f"Row {i}: New candidate '{name}' ({email}) stored successfully "
                            f"at {datetime.utcnow().isoformat()}Z. "
                            f"Status: linkedin_pending. Follow-up email queued."
                        )

                        # Send LinkedIn follow-up email
                        send_followup_email(email, name)

                        # Process CV if provided
                        if cv_url:
                            await process_cv(email, cv_url)

            except Exception as e:
                logger.error(f"Row {i}: Database error while processing '{email}': {e}")
                error_count += 1
                continue

        # TC-01: Poll summary
        logger.info(
            f"Poll complete — "
            f"{success_count} new candidate(s) added, "
            f"{duplicate_count} duplicate(s) updated, "
            f"{error_count} row(s) skipped due to errors."
        )

    except Exception as e:
        logger.error(f"Critical error during sheet polling: {e}") 