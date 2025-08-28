from __future__ import annotations

from typing import Any, Dict, Tuple, List


def resolve_repo(payload: Dict[str, Any], rules: List[Dict[str, Any]], default: Tuple[str, str]) -> Tuple[str, str]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    # Extract common attributes
    team_id = data.get("teamId") or (data.get("team") or {}).get("id")
    labels = {l.get("name") for l in (data.get("labels") or []) if isinstance(l, dict)}
    project_id = data.get("projectId") or (data.get("project") or {}).get("id")

    for rule in rules:
        target = rule.get("target")
        if not target or "/" not in target:
            continue
        # Matchers: any provided must match
        ok = True
        if "teamId" in rule:
            ok = ok and rule["teamId"] == team_id
        if ok and "projectId" in rule:
            ok = ok and rule["projectId"] == project_id
        if ok and "label" in rule:
            ok = ok and (rule["label"] in labels if labels else False)
        if ok and "labelsAny" in rule:
            wanted = set(rule["labelsAny"]) if isinstance(rule["labelsAny"], list) else set()
            ok = ok and bool(labels and (labels & wanted))
        if ok:
            owner, repo = target.split("/", 1)
            return owner, repo
    return default
