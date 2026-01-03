import httpx
import asyncio
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import json
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, access_token: str, redis_client: Optional[redis.Redis] = None):
        self.access_token = access_token
        self.redis = redis_client
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get_cached(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def _set_cached(self, key: str, value: Any, ttl: int = 86400):
        if not self.redis:
            return
        await self.redis.set(key, json.dumps(value), ex=ttl)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)

            # Handle rate limiting
            if response.status_code == 403:
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                if remaining == 0:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_seconds = max(reset_time - datetime.now().timestamp(), 0) + 1
                    if wait_seconds < 3600:  # Don't wait more than an hour
                        await asyncio.sleep(wait_seconds)
                        return await self._request(method, url, **kwargs)

            response.raise_for_status()
            return response

    async def get_starred_repos(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Fetch all starred repositories for the authenticated user"""
        all_repos = []
        page = 1

        while True:
            url = f"{GITHUB_API_BASE}/user/starred?per_page={per_page}&page={page}"
            response = await self._request("GET", url)
            repos = response.json()

            if not repos:
                break

            all_repos.extend(repos)
            page += 1

            # Safety limit
            if page > 50:
                break

        return all_repos

    async def get_repo_stargazers(
        self, owner: str, repo: str, sample_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch stargazers for a repository (sampled)"""
        cache_key = f"stargazers:{owner}/{repo}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/stargazers?per_page={sample_size}"
        try:
            response = await self._request("GET", url)
            stargazers = response.json()
            await self._set_cached(cache_key, stargazers, ttl=86400)  # 24 hours
            return stargazers
        except httpx.HTTPStatusError:
            return []

    async def get_user_starred(
        self, username: str, per_page: int = 100, max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch starred repos for a specific user"""
        cache_key = f"user_starred:{username}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        all_repos = []
        page = 1

        while page <= max_pages:
            url = f"{GITHUB_API_BASE}/users/{username}/starred?per_page={per_page}&page={page}"
            try:
                response = await self._request("GET", url)
                repos = response.json()

                if not repos:
                    break

                all_repos.extend(repos)
                page += 1
            except httpx.HTTPStatusError:
                break

        await self._set_cached(cache_key, all_repos, ttl=604800)  # 7 days
        return all_repos

    async def get_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status"""
        url = f"{GITHUB_API_BASE}/rate_limit"
        response = await self._request("GET", url)
        return response.json()


async def get_github_client(access_token: str) -> GitHubClient:
    """Create a GitHub client with optional Redis caching"""
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
    except Exception:
        redis_client = None

    return GitHubClient(access_token, redis_client)
