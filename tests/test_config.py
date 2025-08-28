import os
import json
import pytest

from app.config import get_settings, validate_settings_or_raise


def _clear_settings_cache():
    # clear lru_cache between tests
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


def test_config_loads_with_required_env(monkeypatch):
    _clear_settings_cache()
    # Ensure required env vars are present (env overrides .env)
    monkeypatch.setenv("GITHUB_OWNER", "acme")
    monkeypatch.setenv("GITHUB_REPO", "demo")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "secret123")

    settings = validate_settings_or_raise()
    assert settings.github_owner == "acme"
    assert settings.github_repo == "demo"
    assert settings.github_token == "ghp_test"
    assert settings.linear_webhook_secret == "secret123"


def test_config_missing_env_raises_runtime_error(monkeypatch, tmp_path):
    _clear_settings_cache()
    # Move CWD to a clean directory so project .env is not picked up
    monkeypatch.chdir(tmp_path)
    # Ensure env vars are absent
    for key in ("GITHUB_OWNER", "GITHUB_REPO", "GITHUB_TOKEN", "LINEAR_WEBHOOK_SECRET"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError) as ei:
        validate_settings_or_raise()

    msg = str(ei.value)
    assert "Invalid or missing environment configuration" in msg

