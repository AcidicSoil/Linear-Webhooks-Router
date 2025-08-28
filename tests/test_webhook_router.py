import json

from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.security.linear import compute_linear_signature
from app.config import get_settings


def sign(body: bytes) -> str:
    secret = get_settings().linear_webhook_secret
    return compute_linear_signature(body, secret)


def test_webhook_accepts_and_reports_route(monkeypatch):
    client = TestClient(app)
    payload = {"type": "Issue", "action": "create", "data": {"id": "lin_1"}}
    body = json.dumps(payload).encode()
    sig = sign(body)
    r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
    assert r.status_code == 200
    data = r.json()
    assert data["accepted"] is True
    assert data["routed"] is False
    assert data["entity"] == "Issue"
    assert data["action"] == "create"


def test_routing_rules_choose_target(monkeypatch):
    # Set routing rules to match teamId and send to alt repo
    settings = get_settings()
    alt = {
        "target": f"{settings.github_owner}/{settings.github_repo}",  # use same, just verifying path
        "teamId": "team-42",
    }
    monkeypatch.setenv("ROUTING_RULES_JSON", json.dumps([alt]))
    client = TestClient(app)
    payload = {"type": "Issue", "action": "create", "data": {"id": "lin_2", "teamId": "team-42"}}
    body = json.dumps(payload).encode()
    sig = sign(body)
    r = client.post("/linear/webhook", data=body, headers={"linear-signature": sig})
    assert r.status_code == 200
