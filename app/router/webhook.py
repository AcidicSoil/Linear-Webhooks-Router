from __future__ import annotations

from typing import Any, Callable, Dict, Tuple
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from ..security.linear import verify_linear_signature
from .events import parse_linear_event
from ..handlers.issue_create import handle_issue_create
from ..handlers.issue_update import handle_issue_update
from ..handlers.issue_close import handle_issue_close
from ..handlers.comment_create import handle_comment_create
from ..logging import get_logger
from ..db.repository import MappingRepository
from ..config import get_settings
from ..routing import resolve_repo


router = APIRouter()


Handler = Callable[[Dict[str, Any], Request], Any]


@router.post("/linear/webhook")
async def handle_linear_webhook(
    request: Request,
    _: None = Depends(verify_linear_signature),
) -> Dict[str, Any]:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    entity, action = parse_linear_event(payload)

    # Placeholder router mapping. Task 7 will register real handlers.
    handler_map: Dict[Tuple[str, str], Handler] = {
        ("Issue", "create"): handle_issue_create,
        ("Issue", "update"): handle_issue_update,
        ("Issue", "close"): handle_issue_close,
        ("Comment", "create"): handle_comment_create,
    }

    handler = handler_map.get((entity, action))
    if handler is None:
        return {"accepted": True, "routed": False, "entity": entity, "action": action}

    try:
        # Determine target repo via rules
        settings = get_settings()
        owner, repo = resolve_repo(payload, settings.routing_rules(), (settings.github_owner, settings.github_repo))
        request.state.target_owner = owner
        request.state.target_repo = repo
        get_logger().info("routing_decision", owner=owner, repo=repo, entity=entity, action=action)
        result = await handler(payload, request)
        return {"accepted": True, "routed": True, "result": result}
    except Exception as exc:
        # Capture into DLQ and return 202 Accepted to avoid retries from Linear
        log = get_logger().bind(entity=entity, action=action)
        log.error("handler_failed", error=str(exc))
        repo: MappingRepository = request.app.state.mapping_repo
        try:
            repo.dlq_insert(f"{entity}.{action}", json.dumps(payload), str(exc))
        except Exception:
            # DLQ write failed; still respond gracefully
            pass
        return {"accepted": True, "routed": True, "error": "captured"}
