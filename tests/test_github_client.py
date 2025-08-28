import asyncio
import httpx
import pytest
import respx

from app.services.github_client import GitHubClient, GITHUB_API


@pytest.mark.asyncio
async def test_headers_and_create_issue():
    client = GitHubClient(token="x")
    async with httpx.AsyncClient(base_url=GITHUB_API) as hc:
        client.client = hc
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.post("/repos/o/r/issues").respond(201, json={"number": 123})
            num = await client.create_issue("o", "r", "t", body="b")
            assert num == 123
            assert route.called
            req = route.calls.last.request
            assert req.headers["Authorization"].startswith("token ")
            assert req.headers["Accept"] == "application/vnd.github+json"


@pytest.mark.asyncio
async def test_retry_on_5xx_then_success():
    client = GitHubClient(token="x")
    async with httpx.AsyncClient(base_url=GITHUB_API, timeout=2.0) as hc:
        client.client = hc
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.post("/repos/o/r/issues").mock(
                side_effect=[
                    httpx.Response(500, json={"message": "boom"}),
                    httpx.Response(201, json={"number": 7}),
                ]
            )
            num = await client.create_issue("o", "r", "t")
            assert num == 7
