import httpx
import logging
from urllib.parse import urlparse
from typing import Dict, Any
from config import settings
from collections import Counter

logger = logging.getLogger(__name__)

async def scrape_github(github_url: str) -> Dict[str, Any]:
    """
    Extracts username from github_url and fetches basic user info and top 5 repos.
    Handles rate limiting, invalid URLs, private/missing profiles gracefully.
    """

    # TC-06: No URL provided
    if not github_url or github_url.strip().lower() == "none":
        logger.warning("GitHub URL is empty or None. Skipping GitHub scrape.")
        return {"error": "no_github_url"}

    try:
        # Extract username from URL
        path = urlparse(github_url.strip()).path
        parts = [p for p in path.split('/') if p]

        if not parts:
            logger.warning(f"Could not extract username from GitHub URL: {github_url}")
            return {"error": "invalid_github_url"}

        username = parts[0]

        # TC-06: Validate username format
        if len(username) < 2 or '.' in username:
            logger.warning(f"Invalid GitHub username '{username}' extracted from URL: {github_url}. "
                           f"Username too short or contains invalid characters.")
            return {"error": "invalid_github_url"}

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TalentRankBot/1.0"
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        async with httpx.AsyncClient() as client:

            # --- Fetch user profile ---
            try:
                user_resp = await client.get(
                    f"https://api.github.com/users/{username}",
                    headers=headers,
                    timeout=10.0
                )
            except httpx.TimeoutException:
                logger.error(f"GitHub API timed out while fetching user profile for '{username}'.")
                return {"error": "github_timeout"}
            except httpx.ConnectError:
                logger.error(f"Could not connect to GitHub API for '{username}'. Check network.")
                return {"error": "github_unavailable"}

            # TC-07: Rate limit on user fetch
            if user_resp.status_code == 403:
                rate_remaining = user_resp.headers.get("X-RateLimit-Remaining", "unknown")
                rate_reset = user_resp.headers.get("X-RateLimit-Reset", "unknown")
                if rate_remaining == "0":
                    logger.warning(
                        f"GitHub API rate limit reached for '{username}'. "
                        f"X-RateLimit-Remaining: 0. "
                        f"Rate limit resets at epoch: {rate_reset}. "
                        f"Skipping scrape — will retry on next poll cycle."
                    )
                    return {"error": "github_rate_limited", "retry": True, "reset_at": rate_reset}
                else:
                    logger.warning(f"GitHub API returned 403 for '{username}' (not rate limit). "
                                   f"Response: {user_resp.text[:200]}")
                    return {"error": "github_forbidden"}

            # TC-06: Profile not found or private
            if user_resp.status_code == 404:
                logger.warning(f"GitHub profile not found for user: '{username}'. "
                               f"Profile may be private, deleted, or URL is incorrect.")
                return {"error": "github_not_found"}

            # Any other non-200 response
            if user_resp.status_code != 200:
                logger.warning(f"GitHub user fetch failed for '{username}'. "
                               f"Status: {user_resp.status_code}. Response: {user_resp.text[:200]}")
                return {"error": "github_unavailable"}

            user_data = user_resp.json()
            logger.info(f"GitHub profile fetched successfully for '{username}'. "
                        f"Public repos: {user_data.get('public_repos', 0)}, "
                        f"Followers: {user_data.get('followers', 0)}.")

            # --- Fetch repositories ---
            top_repos = []
            languages = []
            total_stars = 0

            try:
                repos_resp = await client.get(
                    f"https://api.github.com/users/{username}/repos?sort=stars&per_page=10",
                    headers=headers,
                    timeout=10.0
                )
            except httpx.TimeoutException:
                logger.warning(f"GitHub repos fetch timed out for '{username}'. "
                               f"Returning profile data only without repos.")
                repos_resp = None
            except httpx.ConnectError:
                logger.warning(f"Connection error fetching repos for '{username}'. "
                               f"Returning profile data only.")
                repos_resp = None

            if repos_resp is not None:

                # TC-07: Rate limit on repos fetch
                if repos_resp.status_code == 403:
                    rate_remaining = repos_resp.headers.get("X-RateLimit-Remaining", "unknown")
                    rate_reset = repos_resp.headers.get("X-RateLimit-Reset", "unknown")
                    if rate_remaining == "0":
                        logger.warning(
                            f"GitHub API rate limit reached while fetching repos for '{username}'. "
                            f"X-RateLimit-Remaining: 0. Resets at epoch: {rate_reset}. "
                            f"Returning profile data only without repos."
                        )
                    else:
                        logger.warning(f"GitHub repos fetch returned 403 for '{username}' (not rate limit).")

                elif repos_resp.status_code == 200:
                    repos_data = repos_resp.json()

                    # TC-08: Filter forks, calculate accurate stats
                    non_forks = [r for r in repos_data if not r.get("fork")]

                    for repo in non_forks:
                        total_stars += repo.get("stargazers_count", 0)
                        if repo.get("language"):
                            languages.append(repo.get("language"))

                    # Top 5 by stars
                    top_repos = [
                        {
                            "name": r.get("name"),
                            "description": r.get("description"),
                            "stars": r.get("stargazers_count", 0),
                            "language": r.get("language")
                        }
                        for r in sorted(
                            non_forks,
                            key=lambda x: x.get("stargazers_count", 0),
                            reverse=True
                        )[:5]
                    ]

                    logger.info(
                        f"TC-08: GitHub repos scraped for '{username}'. "
                        f"Total repos: {len(repos_data)}, "
                        f"Non-forks: {len(non_forks)}, "
                        f"Total stars: {total_stars}, "
                        f"Top repo: {top_repos[0]['name'] if top_repos else 'None'}."
                    )

                else:
                    logger.warning(f"GitHub repos fetch returned unexpected status "
                                   f"{repos_resp.status_code} for '{username}'.")

            # TC-08: Calculate primary language accurately
            primary_language = None
            if languages:
                language_counts = Counter(languages)
                primary_language = language_counts.most_common(1)[0][0]
                total = sum(language_counts.values())
                lang_breakdown = {
                    lang: f"{round(count / total * 100)}%"
                    for lang, count in language_counts.most_common()
                }
                logger.info(f"TC-08: Language breakdown for '{username}': {lang_breakdown}.")

            # TC-05: Full successful result log
            logger.info(
                f"TC-05: GitHub scrape complete for '{username}'. "
                f"Public repos: {user_data.get('public_repos', 0)}, "
                f"Top repos extracted: {len(top_repos)}, "
                f"Primary language: {primary_language}, "
                f"Total stars: {total_stars}."
            )

            return {
                "username": username,
                "bio": user_data.get("bio"),
                "public_repos": user_data.get("public_repos"),
                "followers": user_data.get("followers"),
                "company": user_data.get("company"),
                "top_repos": top_repos,
                "primary_language": primary_language,
                "total_stars": total_stars
            }

    except Exception as e:
        logger.error(f"Unexpected error scraping GitHub for '{github_url}': {e}")
        return {"error": "github_unavailable"}