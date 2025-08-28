from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, Request

from ..db.repository import MappingRepository
from ..services.github_client import GitHubClient
from ..config import get_settings
from ..logging import get_logger


def _format_comment(author: str | None, body: str | None) -> str:
    a = author or "Linear user"
    b = body or ""
    return f"From {a} on Linear:\n\n{b}"


async def handle_comment_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    settings = get_settings()
    data = payload.get("data", {})

    # Linear comment payloads typically include the parent issue id
    linear_issue_id = str(data.get("issueId") or data.get("issue") or data.get("issue_id") or "")
    if not linear_issue_id:
        # try nested object
        issue = data.get("issue") or {}
        linear_issue_id = str(issue.get("id") or issue.get("identifier") or "")
    if not linear_issue_id:
        raise HTTPException(status_code=400, detail="missing parent issue id")

    author = (data.get("user") or {}).get("name") if isinstance(data.get("user"), dict) else data.get("user")
    body = data.get("body") or data.get("text")
    gh_body = _format_comment(author if isinstance(author, str) else None, body if isinstance(body, str) else None)

    repo: MappingRepository = request.app.state.mapping_repo
    mapping = repo.get_by_linear_issue_id(linear_issue_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    log = get_logger().bind(linear_issue_id=linear_issue_id, github_issue_number=mapping.github_issue_number)
    gh = GitHubClient(token=settings.github_token)
    try:
        result = await gh.create_comment(
            getattr(request.state, "target_owner", mapping.github_owner),
            getattr(request.state, "target_repo", mapping.github_repo),
            mapping.github_issue_number,
            gh_body,
        )
    finally:
        await gh.aclose()

    log.info("comment_created")
    return {"commented": True, "github_issue_number": mapping.github_issue_number}
