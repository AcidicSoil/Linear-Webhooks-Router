from __future__ import annotations

from typing import Any, Dict, Tuple


def parse_linear_event(payload: Dict[str, Any]) -> Tuple[str, str]:
    """Return (entity, action) for a Linear webhook payload.

    Linear delivers e.g. { "type": "Issue", "action": "create", ... }
    Fallbacks ensure router doesn't crash on unexpected shapes.
    """
    entity = str(payload.get("type") or payload.get("entity") or "unknown")
    action = str(payload.get("action") or payload.get("event") or "unknown")
    return entity, action
