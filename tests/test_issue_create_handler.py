import json
import pytest
import respx
import httpx

from fastapi.testclient import TestClient

from app.main import app
from app.security.linear import compute_linear_signature
from app.config import get_settings
from app.services.github_client import GITHUB_API


def sign(body: bytes) -> str:
    secret = get_settings().linear_webhook_secret
    return compute_linear_signature(body, secret)


@pytest.mark.asyncio
async def test_issue_create_flow(tmp_path):
    # Ensure file-backed DB is clean for test
    app.state.mapping_repo.storage_url = ":memory:"

    payload = {
        "type": "Issue",
        "action": "create",
        "data": {
            "id": "LIN-123",
            "title": "Bug: something broke",
            "description": "Steps to reproduce...",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign(body)

    async with httpx.AsyncClient(base_url=GITHUB_API) as hc:
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.post("/repos/.*/.*/issues").respond(201, json={"number": 99})
            client = TestClient(app)
            r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
            assert r.status_code == 200
            data = r.json()
            assert data["accepted"] is True
            assert data["routed"] is True
            assert data["result"]["github_issue_number"] == 99

