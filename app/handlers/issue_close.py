from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, Request

from ..db.repository import MappingRepository
from ..services.github_client import GitHubClient
from ..config import get_settings
from ..logging import get_logger


TERMINAL_STATES = {"Done", "Archived", "Canceled", "Completed"}


async def handle_issue_close(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    settings = get_settings()
    data = payload.get("data", {})
    linear_issue_id = str(data.get("id") or data.get("identifier") or "")
    if not linear_issue_id:
        raise HTTPException(status_code=400, detail="missing issue id in payload")

    # Many Linear payloads carry state name under data.state.name or similar.
    state = (
        (data.get("state") or {}).get("name")
        or data.get("status")
        or payload.get("state")
        or ""
    )

    repo: MappingRepository = request.app.state.mapping_repo
    mapping = repo.get_by_linear_issue_id(linear_issue_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    log = get_logger().bind(linear_issue_id=linear_issue_id, github_issue_number=mapping.github_issue_number)
    gh = GitHubClient(token=settings.github_token)
    try:
        result = await gh.update_issue(
            getattr(request.state, "target_owner", mapping.github_owner),
            getattr(request.state, "target_repo", mapping.github_repo),
            mapping.github_issue_number,
            state="closed",
        )
    finally:
        await gh.aclose()

    log.info("issue_closed", state=state)
    return {"closed": True, "github_issue_number": mapping.github_issue_number, "state": state}
