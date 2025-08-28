from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from ..db.repository import MappingRepository
import hashlib
from ..services.github_client import GitHubClient
from ..config import get_settings
from ..logging import get_logger


async def handle_issue_update(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    settings = get_settings()
    data = payload.get("data", {})
    linear_issue_id = str(data.get("id") or data.get("identifier") or "")
    if not linear_issue_id:
        raise HTTPException(status_code=400, detail="missing issue id in payload")

    title: Optional[str] = data.get("title")
    description: Optional[str] = data.get("description")

    repo: MappingRepository = request.app.state.mapping_repo
    mapping = repo.get_by_linear_issue_id(linear_issue_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    log = get_logger().bind(linear_issue_id=linear_issue_id, github_issue_number=mapping.github_issue_number)
    # Compute prospective checksum and skip if unchanged
    prospective_body = description if description is not None else ""
    prospective_title = title if title is not None else ""
    new_checksum = hashlib.sha256(f"{prospective_title}\n\n{prospective_body}".encode("utf-8")).hexdigest()
    if mapping.content_checksum == new_checksum:
        log.info("skip_update_noop")
        return {"updated": False, "github_issue_number": mapping.github_issue_number, "skipped": True}

    gh = GitHubClient(token=settings.github_token)
    try:
        result = await gh.update_issue(
            getattr(request.state, "target_owner", mapping.github_owner),
            getattr(request.state, "target_repo", mapping.github_repo),
            mapping.github_issue_number,
            title=title,
            body=description,
        )
    finally:
        await gh.aclose()

    # Update checksum after success
    repo.update_checksum(linear_issue_id, new_checksum)
    log.info("issue_updated")
    return {"updated": True, "github_issue_number": mapping.github_issue_number}
