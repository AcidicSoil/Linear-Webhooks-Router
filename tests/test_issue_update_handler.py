import json
import pytest
import respx
import httpx

from fastapi.testclient import TestClient

from app.main import app
from app.security.linear import compute_linear_signature
from app.config import get_settings
from app.services.github_client import GITHUB_API
from app.db.repository import Mapping


def sign(body: bytes) -> str:
    secret = get_settings().linear_webhook_secret
    return compute_linear_signature(body, secret)


@pytest.mark.asyncio
async def test_issue_update_flow():
    # Seed mapping in memory
    app.state.mapping_repo.storage_url = ":memory:"
    repo = app.state.mapping_repo
    repo.upsert_mapping(Mapping(
        linear_issue_id="LIN-999",
        github_owner=get_settings().github_owner,
        github_repo=get_settings().github_repo,
        github_issue_number=101,
    ))

    payload = {
        "type": "Issue",
        "action": "update",
        "data": {
            "id": "LIN-999",
            "title": "Updated title",
            "description": "Updated body",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign(body)

    async with httpx.AsyncClient(base_url=GITHUB_API) as hc:
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.patch("/repos/.*/.*/issues/101").respond(200, json={"ok": True})
            client = TestClient(app)
            r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
            assert r.status_code == 200
            data = r.json()
            assert data["accepted"] is True
            assert data["routed"] is True
            assert data["result"]["updated"] is True
            assert route.called


@pytest.mark.asyncio
async def test_issue_update_skips_noop():
    # Seed mapping with checksum corresponding to unchanged payload
    app.state.mapping_repo.storage_url = ":memory:"
    repo = app.state.mapping_repo
    repo.upsert_mapping(Mapping(
        linear_issue_id="LIN-abc",
        github_owner=get_settings().github_owner,
        github_repo=get_settings().github_repo,
        github_issue_number=5,
        content_checksum="c0b3b5f5e3f43c0152e2da6035df6b0adf64a3644d419536bf09a2b6d5a64d4c",  # sha256("Updated title\n\nUpdated body")
    ))

    payload = {
        "type": "Issue",
        "action": "update",
        "data": {
            "id": "LIN-abc",
            "title": "Updated title",
            "description": "Updated body",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign(body)

    async with httpx.AsyncClient(base_url=GITHUB_API) as hc:
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.patch("/repos/.*/.*/issues/5").respond(200, json={"ok": True})
            client = TestClient(app)
            r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
            assert r.status_code == 200
            data = r.json()
            assert data["accepted"] is True
            assert data["routed"] is True
            assert data["result"].get("skipped") is True
            assert route.called is False
