import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.linear import compute_linear_signature


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    # Provide required env for app startup validation
    monkeypatch.setenv("GITHUB_OWNER", "acme")
    monkeypatch.setenv("GITHUB_REPO", "demo")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "topsecret")


def test_webhook_accepts_valid_signature():
    body = (
        b'{"type":"Issue","action":"create","data":{"id":"123","title":"t"}}'
    )
    sig = compute_linear_signature(body, "topsecret")

    with TestClient(app) as client:
        resp = client.post(
            "/linear/webhook",
            data=body,
            headers={
                "content-type": "application/json",
                "linear-signature": sig,
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"accepted": True}


def test_webhook_rejects_missing_header():
    with TestClient(app) as client:
        resp = client.post(
            "/linear/webhook",
            data=b"{}",
            headers={"content-type": "application/json"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("missing")


def test_webhook_rejects_invalid_signature():
    body = b"{}"
    with TestClient(app) as client:
        resp = client.post(
            "/linear/webhook",
            data=body,
            headers={
                "content-type": "application/json",
                "linear-signature": "deadbeef",
            },
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "invalid signature"

