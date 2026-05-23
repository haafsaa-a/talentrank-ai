import json
import logging
from groq import Groq
from config import settings

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

# Minimum character threshold across all sources to attempt AI generation
# TC: Empty / Minimal Profile Data — below this = insufficient data
MIN_DATA_THRESHOLD = 50

# Valid domain tags the LLM is allowed to return
VALID_DOMAIN_TAGS = {"Frontend", "Backend", "Fullstack", "ML/AI", "DevOps", "Mobile", "Data", "Design"}


def _fallback_profile(summary: str) -> dict:
    """Returns a safe empty profile dict with a given summary message."""
    return {
        "summary": summary,
        "skills": [],
        "cv_skills": [],
        "cv_experience": [],
        "cv_education": [],
        "top_projects": [],
        "experience_years": 0,
        "domain_tags": [],
        "data_available": False,
    }


def _check_data_sufficiency(github_data: dict, portfolio_text: str, linkedin_data: dict, cv_text: str) -> tuple[bool, list[str]]:
    """
    TC: Empty / Minimal Profile Data
    Checks how much real data is available across all sources.
    Returns (has_enough_data: bool, available_sources: list[str])
    """
    available_sources = []

    if github_data and github_data.get("username") and github_data.get("username") != "N/A":
        available_sources.append("GitHub")

    if linkedin_data and linkedin_data.get("name") and linkedin_data.get("data_available", True):
        available_sources.append("LinkedIn")

    if portfolio_text and isinstance(portfolio_text, str) and len(portfolio_text.strip()) > MIN_DATA_THRESHOLD:
        available_sources.append("Portfolio")

    if cv_text and isinstance(cv_text, str) and len(cv_text.strip()) > MIN_DATA_THRESHOLD:
        available_sources.append("CV")

    return len(available_sources) > 0, available_sources


def _sanitize_profile(profile_data: dict) -> dict:
    """
    TC: Tone & Professionalism / Conflicting Data / Partial Data
    Validates and cleans the LLM response:
    - Ensures all required keys exist with correct types
    - Clamps experience_years to a sane range
    - Filters domain_tags to only allowed values
    - Ensures summary is a non-empty string
    - Adds data_available flag
    """
    # Ensure all keys exist with correct types
    sanitized = {
        "summary":        str(profile_data.get("summary") or "").strip(),
        "skills":         profile_data.get("skills", []) if isinstance(profile_data.get("skills"), list) else [],
        "cv_skills":      profile_data.get("cv_skills", []) if isinstance(profile_data.get("cv_skills"), list) else [],
        "cv_experience":  profile_data.get("cv_experience", []) if isinstance(profile_data.get("cv_experience"), list) else [],
        "cv_education":   profile_data.get("cv_education", []) if isinstance(profile_data.get("cv_education"), list) else [],
        "top_projects":   profile_data.get("top_projects", []) if isinstance(profile_data.get("top_projects"), list) else [],
        "experience_years": 0,
        "domain_tags":    [],
        "data_available": True,
    }

    # TC: Conflicting Data — clamp experience_years to a realistic range (0–50)
    raw_years = profile_data.get("experience_years", 0)
    try:
        sanitized["experience_years"] = max(0, min(50, int(raw_years)))
    except (TypeError, ValueError):
        logger.warning(f"Invalid experience_years value '{raw_years}' — defaulting to 0.")
        sanitized["experience_years"] = 0

    # TC: Filter domain_tags to only allowed values — drop any hallucinated ones
    raw_tags = profile_data.get("domain_tags", [])
    if isinstance(raw_tags, list):
        sanitized["domain_tags"] = [t for t in raw_tags if t in VALID_DOMAIN_TAGS][:3]

    # TC: Tone & Professionalism — summary must be a non-empty string
    if not sanitized["summary"]:
        sanitized["summary"] = "Insufficient information to generate a professional summary."
        sanitized["data_available"] = False

    # Cap skills list at 10 items
    sanitized["skills"] = sanitized["skills"][:10]

    return sanitized


def _strip_markdown(raw: str) -> str:
    """Strips markdown code fences from LLM response."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _build_prompt(context: str, available_sources: list[str]) -> str:
    """
    TC: Partial Data — adjusts prompt instructions based on available sources.
    TC: Conflicting Data — instructs the model to prefer CV and flag conflicts.
    TC: Tone & Professionalism — enforces third-person professional tone.
    """
    source_note = (
        f"Available data sources: {', '.join(available_sources)}. "
        "Only use information from the available sources. "
        "Do NOT invent, assume, or hallucinate any information that is not present in the data."
    ) if available_sources else ""

    conflict_note = (
        "If the same field (e.g. years of experience, skills) appears with conflicting values "
        "across sources, prefer the CV as the primary source. "
        "Do not include contradictory statements in the summary."
    )

    tone_note = (
        "The summary must be written in professional third-person tone "
        "(e.g. 'The candidate is...'), be grammatically correct, formal, "
        "and between 150–300 words."
    )

    return f"""You are an expert technical recruiter AI. Analyze the candidate data below and return ONLY a valid JSON object with these exact keys:
- summary: string, professional third-person summary (150–300 words)
- skills: list of up to 10 skill strings inferred from ALL sources combined
- cv_skills: list of skills explicitly mentioned in the CV/Resume section only
- cv_experience: list of work experience objects from CV: {{company, role, duration}}
- cv_education: list of education objects from CV: {{institution, degree, year}}
- top_projects: list of up to 3 objects with keys: name, description, stars
- experience_years: integer, estimated years of experience using CV as primary signal
- domain_tags: list of 1-3 strings chosen ONLY from: [Frontend, Backend, Fullstack, ML/AI, DevOps, Mobile, Data, Design]

{tone_note}
{conflict_note}
{source_note}

Return ONLY the JSON. No markdown. No explanation. No code fences.

{context}"""


async def generate_profile(
    candidate_id: str,
    github_data: dict,
    portfolio_text: str,
    linkedin_data: dict,
    cv_text: str,
    db_session
) -> dict:
    """
    Merges scrape data, calls Groq LLM, parses response, saves profile to DB.

    Error handling:
      TC-19 — Full data: generates coherent 150-300 word professional summary.
      TC-20 — Partial data: generates summary from available sources only, no hallucination.
      TC-21 — Tone check: prompt enforces third-person, formal, grammatically correct output.
      TC-22 — Conflicting data: prompt instructs LLM to prefer CV; experience_years clamped.
      TC-23 — Empty/minimal data: detected before LLM call; returns 'Insufficient data' message.
    """

    # Sanitize inputs — treat None as empty to avoid .get() crashes
    github_data    = github_data or {}
    linkedin_data  = linkedin_data or {}
    portfolio_text = portfolio_text or ""
    cv_text        = cv_text or ""

    # ------------------------------------------------------------------ #
    # TC-23: Empty / Minimal Profile Data — check before calling LLM     #
    # ------------------------------------------------------------------ #
    has_enough_data, available_sources = _check_data_sufficiency(
        github_data, portfolio_text, linkedin_data, cv_text
    )

    if not has_enough_data:
        logger.warning(f"Insufficient data to generate profile for candidate {candidate_id}.")
        profile_data = _fallback_profile("Insufficient data to generate a profile for this candidate.")
        # Still save to DB so dashboard shows the correct state
        await _save_profile(candidate_id, profile_data, github_data, portfolio_text, linkedin_data, cv_text, db_session)
        return profile_data

    logger.info(f"Generating profile for {candidate_id} with sources: {available_sources}")

    # Normalize portfolio_text to string
    if isinstance(portfolio_text, dict):
        portfolio_text_str = portfolio_text.get('text', '')
    elif isinstance(portfolio_text, str):
        portfolio_text_str = portfolio_text
    else:
        portfolio_text_str = str(portfolio_text) if portfolio_text else ''
    context = f"""
--- LINKEDIN ---
Name: {linkedin_data.get('name', 'N/A')}
Headline: {linkedin_data.get('headline', 'N/A')}
Email: {linkedin_data.get('email', 'N/A')}

--- CV / RESUME ---
{cv_text or 'No CV submitted.'}

--- GITHUB ---
Username: {github_data.get('username', 'N/A')}
Bio: {github_data.get('bio', 'N/A')}
Public Repos: {github_data.get('public_repos', 0)}
Top Projects: {', '.join([f"{r['name']} ({r.get('stars', 0)} stars)" for r in github_data.get('top_repos', [])])}
Primary Language: {github_data.get('primary_language', 'N/A')}
Total Stars: {github_data.get('total_stars', 0)}

--- PORTFOLIO ---
{portfolio_text_str or 'No portfolio data available.'}
"""

    # TC-20 / TC-21 / TC-22: prompt includes tone, conflict, and partial-data instructions
    prompt = _build_prompt(context, available_sources)
    profile_data = None

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert technical recruiter AI. Always respond with valid JSON only, no markdown, no explanation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        # --- Error: empty or missing response from Groq ---
        if not response.choices or not response.choices[0].message.content:
            logger.error(f"Groq returned empty response for candidate {candidate_id}.")
            profile_data = _fallback_profile("Profile generation failed — no response from AI.")
        else:
            raw = _strip_markdown(response.choices[0].message.content.strip())
            profile_data = json.loads(raw)
            # TC-21 / TC-22: sanitize and validate the parsed output
            profile_data = _sanitize_profile(profile_data)
            logger.info(f"Groq profile generated successfully for candidate {candidate_id}")

    except json.JSONDecodeError:
        # --- Error: LLM returned non-JSON — retry with stricter prompt ---
        logger.warning(f"JSON parse failed for {candidate_id}, retrying with stricter prompt...")
        try:
            retry_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON generator. Return only raw valid JSON, nothing else."
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nIMPORTANT: Return only the raw JSON object. No markdown. No backticks. No explanation."
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            raw = _strip_markdown(retry_response.choices[0].message.content.strip())
            profile_data = _sanitize_profile(json.loads(raw))
            logger.info(f"Retry succeeded for candidate {candidate_id}")
        except Exception as e:
            logger.error(f"Retry also failed for {candidate_id}: {e}")
            profile_data = _fallback_profile("Profile parsing failed after retry.")

    except Exception as e:
        # --- Error: Groq API timeout, network error, rate limit, etc. ---
        logger.error(f"Groq API error for {candidate_id}: {e}")
        profile_data = _fallback_profile("Profile generation failed due to an API error.")

    await _save_profile(candidate_id, profile_data, github_data, portfolio_text, linkedin_data, cv_text, db_session)
    return profile_data


async def _save_profile(
    candidate_id: str,
    profile_data: dict,
    github_data: dict,
    portfolio_text: str,
    linkedin_data: dict,
    cv_text: str,
    db_session
) -> None:
    """Saves or updates the profile in the DB and marks candidate status as done."""
    try:
        from models.profile import Profile
        from models.candidate import Candidate, CandidateStatus
        from sqlalchemy import select
        from datetime import datetime
        import uuid

        async with db_session() as session:
            async with session.begin():
                existing = await session.execute(
                    select(Profile).where(Profile.candidate_id == uuid.UUID(candidate_id))
                )
                existing_profile = existing.scalar_one_or_none()
                portfolio_text_str = portfolio_text if isinstance(portfolio_text, str) else portfolio_text.get('text', '') if isinstance(portfolio_text, dict) else str(portfolio_text)
                if existing_profile:
                    existing_profile.summary          = profile_data.get("summary")
                    existing_profile.skills           = profile_data.get("skills", [])
                    existing_profile.top_projects     = profile_data.get("top_projects", [])
                    existing_profile.experience_years = profile_data.get("experience_years")
                    existing_profile.domain_tags      = profile_data.get("domain_tags", [])
                    existing_profile.raw_github_data  = github_data
                    existing_profile.raw_portfolio_text = portfolio_text_str
                    existing_profile.raw_linkedin_data  = linkedin_data
                    existing_profile.generated_at     = datetime.utcnow()
                    existing_profile.cv_skills        = profile_data.get("cv_skills", [])
                    existing_profile.cv_experience    = profile_data.get("cv_experience", [])
                    existing_profile.cv_education     = profile_data.get("cv_education", [])
                    existing_profile.raw_cv_text      = cv_text
                else:
                    profile = Profile(
                        id=uuid.uuid4(),
                        candidate_id=uuid.UUID(candidate_id),
                        summary=profile_data.get("summary"),
                        skills=profile_data.get("skills", []),
                        top_projects=profile_data.get("top_projects", []),
                        experience_years=profile_data.get("experience_years"),
                        domain_tags=profile_data.get("domain_tags", []),
                        raw_github_data=github_data,
                        raw_portfolio_text=portfolio_text_str,
                        raw_linkedin_data=linkedin_data,
                        generated_at=datetime.utcnow(),
                        cv_skills=profile_data.get("cv_skills", []),
                        cv_experience=profile_data.get("cv_experience", []),
                        cv_education=profile_data.get("cv_education", []),
                        raw_cv_text=cv_text
                    )
                    session.add(profile)

                stmt = select(Candidate).where(Candidate.id == uuid.UUID(candidate_id))
                result = await session.execute(stmt)
                candidate = result.scalar_one_or_none()
                if candidate:
                    candidate.status = CandidateStatus.done

        logger.info(f"Profile saved successfully for candidate {candidate_id}")

    except Exception as e:
        logger.error(f"Failed to save profile for {candidate_id}: {e}")