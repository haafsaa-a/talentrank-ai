import httpx
import logging
import re
from bs4 import BeautifulSoup
from typing import Tuple

logger = logging.getLogger(__name__)

# --- Constants ---
JINA_BASE_URL = "https://r.jina.ai/"        # JS-rendered site fallback
MAX_TEXT_LENGTH = 3000
REQUEST_TIMEOUT = 15.0
JINA_TIMEOUT = 20.0                          # Jina takes a bit longer (headless render)

# Domains known to be JS-rendered SPAs — go straight to Jina
JS_HEAVY_DOMAINS = {
    "vercel.app", "netlify.app", "github.io",
    "webflow.io", "framer.app", "cargo.site"
}


def _empty_result(reason: str) -> Tuple[str, str]:
    """Returns (empty text, error reason) for failed scrapes."""
    return "", reason


def _is_js_heavy(url: str) -> bool:
    """Checks if a URL belongs to a known JS-rendered hosting domain."""
    for domain in JS_HEAVY_DOMAINS:
        if domain in url:
            return True
    return False


def _is_meaningful(text: str, min_chars: int = 100) -> bool:
    """
    TC-14: Checks if extracted text is actually useful content.
    If BeautifulSoup gets a JS bundle instead of real content, the
    extracted text will be very short or gibberish — catch that here.
    """
    return len(text.strip()) >= min_chars


def _extract_text_from_html(html: str) -> str:
    """Parses HTML and extracts visible text from relevant tags."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text_blocks = []
    for tag in soup(["p", "h1", "h2", "h3", "h4", "li", "span", "a", "section", "article"]):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            text_blocks.append(text)

    full_text = " ".join(text_blocks)
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    return full_text[:MAX_TEXT_LENGTH]


async def _scrape_via_jina(url: str) -> Tuple[str, str | None]:
    """
    TC-14: Fetches a JS-rendered page via r.jina.ai which headlessly renders
    the page and returns clean markdown/text content.
    Returns (text, error_or_None).
    """
    jina_url = f"{JINA_BASE_URL}{url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TalentRankBot/1.0)",
        "Accept": "text/plain",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jina_url, headers=headers, timeout=JINA_TIMEOUT, follow_redirects=True)

            if resp.status_code == 200:
                text = resp.text.strip()[:MAX_TEXT_LENGTH]
                if _is_meaningful(text):
                    logger.info(f"Jina render succeeded for {url} ({len(text)} chars)")
                    return text, None
                else:
                    logger.warning(f"Jina returned content but it's too short/empty for {url}")
                    return _empty_result("Jina render returned no meaningful content.")

            elif resp.status_code == 404:
                logger.warning(f"Jina reported 404 for {url}")
                return _empty_result("Portfolio page not found (404 via Jina).")

            else:
                logger.warning(f"Jina returned status {resp.status_code} for {url}")
                return _empty_result(f"Jina render failed with status {resp.status_code}.")

    except httpx.TimeoutException:
        logger.error(f"Jina render timed out for {url}")
        return _empty_result("Portfolio JS render timed out.")

    except httpx.RequestError as e:
        logger.error(f"Jina network error for {url}: {e}")
        return _empty_result("Network error during JS render.")


async def scrape_portfolio(portfolio_url: str) -> dict:
    """
    Scrapes the given portfolio URL and returns structured result.

    Strategy:
      1. Validate URL input.
      2. If domain is known JS-heavy → skip static scrape, go straight to Jina (TC-14).
      3. Try static scrape with BeautifulSoup (TC-12).
      4. If static scrape yields thin/empty content → fallback to Jina (TC-14).
      5. On 404 / timeout / unreachable → mark unavailable, don't crash (TC-13).

    Returns:
      {
        "text":           str,   # extracted content (empty string if failed)
        "data_available": bool,  # False if scrape failed
        "method":         str,   # "static" | "jina" | "none"
        "error":          str | None
      }
    """

    
    # Input validation                                                     
    
    if not portfolio_url or not isinstance(portfolio_url, str):
        logger.warning("scrape_portfolio called with empty or invalid URL.")
        return {"text": "", "data_available": False, "method": "none",
                "error": "No portfolio URL provided."}

    portfolio_url = portfolio_url.strip()

    # catch the literal string "None" stored from earlier bug
    if portfolio_url.lower() in ("none", "null", "n/a", "na", ""):
        logger.warning(f"Portfolio URL is placeholder value: '{portfolio_url}'")
        return {"text": "", "data_available": False, "method": "none",
                "error": "Portfolio URL is empty or placeholder."}

    # Ensure scheme
    if not portfolio_url.startswith("http"):
        portfolio_url = "https://" + portfolio_url

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TalentRankBot/1.0)"
    }

   
    # Skip static scrape entirely for known JS-heavy domains       

    if _is_js_heavy(portfolio_url):
        logger.info(f"JS-heavy domain detected for {portfolio_url} — using Jina directly.")
        text, error = await _scrape_via_jina(portfolio_url)
        return {
            "text": text,
            "data_available": bool(text),
            "method": "jina" if text else "none",
            "error": error,
        }

    
    # Static scrape attempt                                
  
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                portfolio_url, headers=headers,
                timeout=REQUEST_TIMEOUT, follow_redirects=True
            )

            # 404 or other HTTP errors
            if resp.status_code == 404:
                logger.warning(f"Portfolio not found (404): {portfolio_url}")
                return {"text": "", "data_available": False, "method": "none",
                        "error": "Portfolio page not found (404)."}

            if resp.status_code != 200:
                logger.warning(f"Portfolio fetch failed for {portfolio_url}: HTTP {resp.status_code}")
                return {"text": "", "data_available": False, "method": "none",
                        "error": f"Portfolio unavailable (HTTP {resp.status_code})."}

            # Extract text via BeautifulSoup
            text = _extract_text_from_html(resp.text)

            #  If content looks like an empty JS shell, fall back to Jina
            if not _is_meaningful(text):
                logger.info(
                    f"Static scrape returned thin content for {portfolio_url} "
                    f"({len(text)} chars) — falling back to Jina."
                )
                text, error = await _scrape_via_jina(portfolio_url)
                return {
                    "text": text,
                    "data_available": bool(text),
                    "method": "jina" if text else "none",
                    "error": error,
                }

            logger.info(f"Static scrape succeeded for {portfolio_url} ({len(text)} chars)")
            return {"text": text, "data_available": True, "method": "static", "error": None}

    # Connection timeout
    except httpx.TimeoutException:
        logger.error(f"Portfolio request timed out: {portfolio_url}")
        return {"text": "", "data_available": False, "method": "none",
                "error": "Portfolio request timed out."}

    # Unreachable / DNS failure / connection refused
    except httpx.RequestError as e:
        logger.error(f"Portfolio unreachable {portfolio_url}: {e}")
        return {"text": "", "data_available": False, "method": "none",
                "error": "Portfolio URL is unreachable."}

    except Exception as e:
        logger.error(f"Unexpected error scraping portfolio {portfolio_url}: {e}")
        return {"text": "", "data_available": False, "method": "none",
                "error": "Unexpected error during portfolio scraping."}