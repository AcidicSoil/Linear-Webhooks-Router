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
async def test_comment_create_flow():
    # Seed mapping in memory
    app.state.mapping_repo.storage_url = ":memory:"
    repo = app.state.mapping_repo
    repo.upsert_mapping(Mapping(
        linear_issue_id="LIN-314",
        github_owner=get_settings().github_owner,
        github_repo=get_settings().github_repo,
        github_issue_number=303,
    ))

    payload = {
        "type": "Comment",
        "action": "create",
        "data": {
            "issueId": "LIN-314",
            "user": {"name": "Ada"},
            "body": "Looks good!",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign(body)

    async with httpx.AsyncClient(base_url=GITHUB_API) as hc:
        with respx.mock(base_url=GITHUB_API) as router:
            route = router.post("/repos/.*/.*/issues/303/comments").respond(201, json={"id": 1})
            client = TestClient(app)
            r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
            assert r.status_code == 200
            data = r.json()
            assert data["accepted"] is True
            assert data["routed"] is True
            assert data["result"]["commented"] is True
            assert route.called

