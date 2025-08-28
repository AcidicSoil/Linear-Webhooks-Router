import json
import pytest
import httpx
import respx

from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.security.linear import compute_linear_signature


def sign(body: bytes) -> str:
    secret = get_settings().linear_webhook_secret
    return compute_linear_signature(body, secret)


def test_dlq_capture_on_failure(monkeypatch):
    # Force a handler failure by using an invalid GitHub token and mocking API to 401
    app.state.mapping_repo.storage_url = ":memory:"
    payload = {"type": "Issue", "action": "create", "data": {"id": "DLQ-1", "title": "t"}}
    body = json.dumps(payload).encode()
    sig = sign(body)

    # Mock GitHub to reply 401 so create_issue raises
    from app.services.github_client import GITHUB_API
    with respx.mock(base_url=GITHUB_API) as router:
        router.post("/repos/.*/.*/issues").respond(401, json={"message": "bad creds"})
        client = TestClient(app)
        r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
        assert r.status_code == 200
        data = r.json()
        assert data.get("error") == "captured"

    # Ensure entry exists in DLQ
    rows = app.state.mapping_repo.dlq_list()
    assert len(rows) >= 1
    assert any("Issue.create" in row["event_type"] for row in rows)

