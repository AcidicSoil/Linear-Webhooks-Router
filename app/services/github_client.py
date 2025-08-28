from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential, RetryCallState


GITHUB_API = "https://api.github.com"


@dataclass
class GitHubClient:
    token: str
    base_url: str = GITHUB_API
    client: Optional[httpx.AsyncClient] = None
    user_agent: str = "linear-webhooks-router/0.1"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _ensure_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)
        return self.client

    async def aclose(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def _retryable(exc: BaseException) -> bool:  # type: ignore[no-redef]
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            return status >= 500 or status == 429
        if isinstance(exc, httpx.TransportError):
            return True
        return False

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        client = self._ensure_client()
        headers = kwargs.pop("headers", {})
        headers = {**self._headers(), **headers}
        last_resp: Optional[httpx.Response] = None
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception(self._retryable),
            reraise=True,
        ):
            with attempt:
                resp = await client.request(method, url, headers=headers, **kwargs)
                last_resp = resp
                if resp.status_code >= 400:
                    # Honor Retry-After for 429/5xx if present (tenacity handles waits between attempts)
                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        raise
                # success
        assert last_resp is not None
        rl = {
            k: last_resp.headers.get(k)
            for k in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset")
        }
        last_resp._rate_limit = rl  # type: ignore[attr-defined]
        return last_resp

    # --- Issues & Comments ---
    async def create_issue(self, owner: str, repo: str, title: str, body: Optional[str] = None, labels: Optional[list[str]] = None) -> int:
        payload: Dict[str, Any] = {"title": title}
        if body is not None:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        resp = await self._request("POST", f"/repos/{owner}/{repo}/issues", json=payload)
        data = resp.json()
        return int(data["number"])  # issue number

    async def update_issue(self, owner: str, repo: str, number: int, *, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        resp = await self._request("PATCH", f"/repos/{owner}/{repo}/issues/{number}", json=payload)
        return resp.json()

    async def create_comment(self, owner: str, repo: str, number: int, body: str) -> Dict[str, Any]:
        payload = {"body": body}
        resp = await self._request("POST", f"/repos/{owner}/{repo}/issues/{number}/comments", json=payload)
        return resp.json()
