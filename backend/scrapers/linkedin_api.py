import httpx
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# --- Constants ---
MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds — doubles on each retry (2, 4, 8)

# HTTP status codes that indicate rate limiting / anti-bot blocks 
RATE_LIMIT_STATUSES = {429, 999}

# HTTP status codes that indicate restricted/private profile 
RESTRICTED_STATUSES = {401, 403}


def _empty_result(error: str = None) -> Dict[str, Any]:
    """Returns a clean empty result dict with an optional error message."""
    return {
        "name": None,
        "email": None,
        "headline": None,
        "profile_picture_url": None,
        "error": error,           # surfaced to dashboard/logs
        "data_available": False,  # dashboard reads this flag
    }


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    timeout: float = 10.0,
) -> httpx.Response | None:
    """
    Performs a GET request with exponential back-off retry on rate-limit responses.
    TC-11: handles rapid requests / anti-bot / CAPTCHA blocks gracefully.
    Returns None if all retries are exhausted or a non-retryable error occurs.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, headers=headers, timeout=timeout)

            # Rate limited or bot-detected — back off and retry
            if resp.status_code in RATE_LIMIT_STATUSES:
                wait = BACKOFF_BASE ** attempt
                logger.warning(
                    f"LinkedIn rate-limit/anti-bot on {url} "
                    f"(status {resp.status_code}), attempt {attempt}/{MAX_RETRIES}. "
                    f"Retrying in {wait}s..."
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.error(
                        f"All {MAX_RETRIES} retries exhausted for {url} due to rate limiting."
                    )
                    return resp  # return the last response so caller can inspect status

            # Any other status — return immediately (caller decides what to do)
            return resp

        except httpx.TimeoutException:
            wait = BACKOFF_BASE ** attempt
            logger.warning(
                f"Timeout on {url}, attempt {attempt}/{MAX_RETRIES}. "
                f"Retrying in {wait}s..."
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(wait)
            else:
                logger.error(f"All retries exhausted for {url} due to timeout.")
                return None

        except httpx.RequestError as e:
            logger.error(f"Network error on {url}: {e}")
            return None

    return None


async def fetch_linkedin_profile(access_token: str) -> Dict[str, Any]:
    """
    Fetches LinkedIn profile data using the OAuth access token.
    Uses openid, profile, and email scopes (/v2/userinfo).
    Falls back to /v2/me for name/headline if available.

    Error handling:
       Happy path: returns name, email, profile picture, headline.
       Private/restricted profile (401/403): returns empty result with
               error='LinkedIn data unavailable' and data_available=False.
       Anti-bot / rate limit (429/999): exponential back-off retry;
               returns empty result with error message if all retries fail.
    """

    # --- Input validation ---
    if not access_token or not isinstance(access_token, str) or not access_token.strip():
        logger.error("fetch_linkedin_profile called with missing or invalid access_token.")
        return _empty_result(error="Invalid access token provided.")

    headers = {"Authorization": f"Bearer {access_token.strip()}"}
    result = {
        "name": None,
        "email": None,
        "headline": None,
        "profile_picture_url": None,
        "error": None,
        "data_available": False,
    }

    async with httpx.AsyncClient() as client:

        
        # Step 1 — /v2/userinfo  (OIDC — name, email, picture)               
        
        userinfo_resp = await _get_with_retry(
            client, "https://api.linkedin.com/v2/userinfo", headers
        )

        if userinfo_resp is None:
            # Network/timeout failure with no response at all
            logger.error("LinkedIn userinfo request failed completely (no response).")
            return _empty_result(error="LinkedIn request failed — network error or timeout.")

        if userinfo_resp.status_code in RESTRICTED_STATUSES:
            # private or restricted profile
            logger.warning(
                f"LinkedIn userinfo restricted (status {userinfo_resp.status_code}). "
                "Profile may be private or token lacks permission."
            )
            return _empty_result(error="LinkedIn data unavailable")

        if userinfo_resp.status_code in RATE_LIMIT_STATUSES:
            # still rate limited after all retries
            logger.error("LinkedIn userinfo blocked by rate limiting after all retries.")
            return _empty_result(error="LinkedIn temporarily blocked — rate limit exceeded.")

        if userinfo_resp.status_code == 200:
            try:
                data = userinfo_resp.json()
                result["name"] = data.get("name")
                result["email"] = data.get("email")
                result["profile_picture_url"] = data.get("picture")
                result["data_available"] = True
                logger.info(f"LinkedIn userinfo fetched successfully for {result['email']}")
            except Exception as e:
                logger.error(f"Failed to parse LinkedIn userinfo JSON: {e}")
                return _empty_result(error="Failed to parse LinkedIn response.")
        else:
            logger.warning(
                f"Unexpected status from LinkedIn userinfo: "
                f"{userinfo_resp.status_code} — {userinfo_resp.text[:200]}"
            )

       
        # Step 2 — /v2/me  (localized name + headline) 
        
        me_resp = await _get_with_retry(
            client, "https://api.linkedin.com/v2/me", headers
        )

        if me_resp is None:
            # Non-fatal — we already have userinfo data if Step 1 succeeded
            logger.warning("LinkedIn /v2/me request failed — skipping headline/name fallback.")

        elif me_resp.status_code in RESTRICTED_STATUSES:
            # 403 on /v2/me is common on free tier — not fatal, log and move on
            logger.warning(
                f"LinkedIn /v2/me returned {me_resp.status_code} — "
                "headline/localized name unavailable (free tier restriction)."
            )

        elif me_resp.status_code in RATE_LIMIT_STATUSES:
            # rate limited on /v2/me — log but don't fail the whole result
            logger.warning("LinkedIn /v2/me rate limited — skipping.")

        elif me_resp.status_code == 200:
            try:
                me_data = me_resp.json()

                # Fallback name if userinfo didn't provide one
                if not result["name"]:
                    first = me_data.get("localizedFirstName", "")
                    last = me_data.get("localizedLastName", "")
                    full_name = f"{first} {last}".strip()
                    if full_name:
                        result["name"] = full_name
                        result["data_available"] = True

                # Headline (free tier might not return this)
                if "localizedHeadline" in me_data:
                    result["headline"] = me_data["localizedHeadline"]

            except Exception as e:
                logger.warning(f"Failed to parse LinkedIn /v2/me JSON: {e}")
        else:
            logger.warning(
                f"Unexpected status from LinkedIn /v2/me: "
                f"{me_resp.status_code} — {me_resp.text[:200]}"
            )

    return result