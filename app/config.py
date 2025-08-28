from functools import lru_cache
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, StringConstraints, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment and optional .env file.

    Required at startup to enable fail-fast behavior.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    github_owner: str = Field(..., alias="GITHUB_OWNER")
    github_repo: str = Field(..., alias="GITHUB_REPO")
    github_token: str = Field(..., alias="GITHUB_TOKEN")
    linear_webhook_secret: str = Field(..., alias="LINEAR_WEBHOOK_SECRET")

    # Optional settings
    routing_rules_json: Optional[str] = Field(None, alias="ROUTING_RULES_JSON")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    storage_url: Optional[str] = Field(None, alias="STORAGE_URL")
    # Default DB path if not set
    def db_url(self) -> str:
        return self.storage_url or "data/app.db"

    def routing_rules(self) -> List[Dict[str, Any]]:
        import json
        if not self.routing_rules_json:
            return []
        try:
            rules = json.loads(self.routing_rules_json)
            assert isinstance(rules, list)
            return rules
        except Exception:
            raise RuntimeError("Invalid ROUTING_RULES_JSON; expected JSON list of rules")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, raising ValidationError if any required are missing."""
    return Settings()  # type: ignore[arg-type]


def validate_settings_or_raise() -> Settings:
    """Helper to trigger validation at startup and return settings.

    FastAPI can call this in an event handler to fail-fast if env is misconfigured.
    """
    try:
        return get_settings()
    except ValidationError as e:
        # Re-raise with a concise message suitable for logs/startup failures
        raise RuntimeError(f"Invalid or missing environment configuration: {e}")
