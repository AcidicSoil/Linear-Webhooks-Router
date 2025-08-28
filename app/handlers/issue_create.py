from __future__ import annotations

from typing import Any, Dict

from fastapi import Request

from ..config import get_settings
from ..db.repository import Mapping, MappingRepository
from ..services.github_client import GitHubClient
from ..logging import get_logger
import hashlib


def _format_github_body(linear_issue_id: str, description: str | None) -> str:
    url = f"https://linear.app/issue/{linear_issue_id}" if linear_issue_id else ""
    desc = description or ""
    parts = [desc]
    if url:
        parts.append("")
        parts.append(f"---\nSource: Linear [{linear_issue_id}]({url})")
    return "\n".join(parts).strip()


async def handle_issue_create(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    settings = get_settings()

    data = payload.get("data", {})
    linear_issue_id = data.get("id") or data.get("identifier") or ""
    title = data.get("title") or "New issue from Linear"
    description = data.get("description")

    body = _format_github_body(str(linear_issue_id), description)

    # Resolve target owner/repo (routing rules later); default to settings
    owner = getattr(request.state, "target_owner", settings.github_owner)
    repo = getattr(request.state, "target_repo", settings.github_repo)

    # Use app-scoped resources
    mapping_repo: MappingRepository = request.app.state.mapping_repo
    log = get_logger().bind(linear_issue_id=linear_issue_id, owner=owner, repo=repo)
    gh = GitHubClient(token=settings.github_token)
    try:
        number = await gh.create_issue(owner, repo, title, body=body, labels=["source:linear"])  # type: ignore[arg-type]
    finally:
        await gh.aclose()

    checksum = hashlib.sha256(f"{title}\n\n{body}".encode("utf-8")).hexdigest()
    mapping = Mapping(
        linear_issue_id=str(linear_issue_id),
        github_owner=owner,
        github_repo=repo,
        github_issue_number=number,
        content_checksum=checksum,
    )
    stored = mapping_repo.upsert_mapping(mapping)
    log.info("issue_created_and_mapped", github_issue_number=stored.github_issue_number)
    return {"github_issue_number": stored.github_issue_number}
