#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  echo "Usage: $0 owner/repo" >&2
  exit 1
fi

say() { printf "\n%s\n" "$*"; }

# --------------------------------------------------------------------
# Milestones
# --------------------------------------------------------------------
MILESTONES=(
  "M1|Setup & Scaffolding"
  "M2|Security & Core Plumbing"
  "M3|GitHub Client & E2E Create"
  "M4|Updates, Close, Comments"
  "M5|Observability & Reliability"
  "M6|Docs & Release"
  "M7|Enhancements"
)

say "Ensuring milestones…"
for m in "${MILESTONES[@]}"; do
  KEY="${m%%|*}"
  DESC="${m#*|}"
  if ! gh api repos/$REPO/milestones --jq '.[].title' | grep -qx "$KEY"; then
    gh api repos/$REPO/milestones -X POST -f title="$KEY" -f description="$DESC" >/dev/null
    echo "  - Created milestone $KEY"
  else
    echo "  - Exists: $KEY"
  fi
done

# --------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------
LABELS=(
  "enhancement|a2eeef|New feature"
  "bug|d73a4a|Bug"
  "docs|0075ca|Documentation"
  "security|b60205|Security-related"
  "backend|5319e7|Backend work"
  "database|b60205|Database schema"
  "integration|0e8a16|External integrations"
  "observability|fbca04|Logs/metrics/tracing"
  "reliability|1d76db|Resilience & recovery"
  "tooling|0052cc|Dev tooling/CLI"
  "config|c2e0c6|Configuration & flags"
  "performance|fef2c0|Performance & efficiency"
  "research|bfdadc|Exploratory work"
  "backlog|d4c5f9|Future/unscheduled"
  "source:linear|ededed|Created by Linear"
)

say "Ensuring labels…"
for l in "${LABELS[@]}"; do
  NAME="${l%%|*}"
  REST="${l#*|}"
  COLOR="${REST%%|*}"
  DESC="${REST#*|}"
  if ! gh label list --repo "$REPO" --limit 500 --json name --jq '.[].name' | grep -qx "$NAME"; then
    gh label create "$NAME" --repo "$REPO" --color "$COLOR" --description "$DESC" || true
    echo "  - Created label $NAME"
  else
    gh label edit "$NAME" --repo "$REPO" --color "$COLOR" --description "$DESC" >/dev/null
    echo "  - Updated label $NAME"
  fi
done

# --------------------------------------------------------------------
# Issues
# --------------------------------------------------------------------
create_issue() {
  local title="$1" milestone="$2" labels="$3" body="$4"

  # skip if already exists
  if gh issue list --repo "$REPO" --state all --json title --jq '.[].title' | grep -qx "$title"; then
    echo "  - Skipping existing: $title"
    return
  fi

  gh issue create --repo "$REPO" \
    --title "$title" \
    --body "$body" \
    ${milestone:+--milestone "$milestone"} \
    $(for lbl in ${labels//,/ }; do echo --label "$lbl"; done)

  echo "  - Created: $title"
}

say "Creating issues…"

# ---------------- M1 ----------------
create_issue \
"Setup FastAPI Application Skeleton and Health Check" "M1" "enhancement,backend" \
"**Context**
Initialize FastAPI project with /health endpoint.

**Acceptance Criteria**
- App starts without error
- GET /health returns {\"status\":\"ok\"}
- Project structure committed with pinned deps
- Basic CI runs lint & tests"

create_issue \
"Implement Environment Variable Configuration Layer" "M1" "enhancement,security" \
"**Context**
Use Pydantic settings to validate GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN, LINEAR_WEBHOOK_SECRET.

**Acceptance Criteria**
- Boot fails if any required secret missing
- Unit tests for valid/missing/invalid values
- .env.example includes all keys
- Secrets never logged"

# ---------------- M2 ----------------
create_issue \
"Implement Linear Webhook Signature Verification" "M2" "security,backend" \
"**Context**
Validate HMAC-SHA256 signature from 'linear-signature' header.

**Acceptance Criteria**
- Missing header → 400; invalid → 403
- Valid signature passes
- Unit tests for valid/invalid/tampered
- No secrets in errors/logs"

create_issue \
"Create SQLite Mapping Store and Repository Layer" "M2" "backend,database" \
"**Context**
Maintain linear_issue_id ↔ github_issue_number mapping.

**Acceptance Criteria**
- Schema with PK/UNIQUE, timestamps, optional checksum
- Upsert prevents duplicates
- Tests for CRUD/uniqueness
- Migration script provided"

create_issue \
"Implement Webhook Endpoint and Event Router" "M2" "backend" \
"**Context**
Expose POST /linear/webhook that verifies signature and dispatches events.

**Acceptance Criteria**
- Routes issue/comment events
- Handlers registered via registry
- Unknown events logged
- Manual payload test routes correctly"

# ---------------- M3 ----------------
create_issue \
"Build Authenticated GitHub API Client" "M3" "backend,integration" \
"**Context**
httpx wrapper for GitHub REST API.

**Acceptance Criteria**
- create_issue, update_issue, create_comment methods
- Retries/backoff on 5xx/429
- Mocked tests for headers/retries/errors
- Rate-limit logging included"

create_issue \
"Implement Handler for Linear “Issue Create” Events" "M3" "backend,integration,source:linear" \
"**Context**
On issue.create, create GitHub issue, add mapping + backlink.

**Acceptance Criteria**
- GitHub issue created with source:linear label
- Mapping stored correctly
- E2E test with signed payload passes
- Idempotent on retries"

# ---------------- M4 ----------------
create_issue \
"Implement Handler for Linear “Issue Update” Events" "M4" "backend" \
"**Context**
On issue.update, patch mapped GitHub issue.

**Acceptance Criteria**
- Lookup mapping; apply only changed fields
- Logs show diff summary
- E2E update test passes
- Missing mapping handled safely"

create_issue \
"Implement Handler for Linear “Issue Close” Events" "M4" "backend" \
"**Context**
On Done/Archived, close mapped GitHub issue.

**Acceptance Criteria**
- Closing reflected in GitHub
- Idempotent if already closed
- E2E test demonstrates closure
- Logs state transitions"

create_issue \
"Implement Handler for Linear “Comment Create” Events" "M4" "backend" \
"**Context**
Mirror Linear comments to GitHub.

**Acceptance Criteria**
- Comment posted to mapped issue
- Includes author + Linear link
- E2E validation passes
- Supports long comments"

# ---------------- M5 ----------------
create_issue \
"Implement Structured JSON Logging and Error Handling" "M5" "observability" \
"**Context**
Add structlog JSON logs and global exception handler.

**Acceptance Criteria**
- Logs include ts, level, request_id, metadata
- Sanitized JSON error responses
- External failures logged with retries
- Sampling/toggles documented"

create_issue \
"Implement a Dead-Letter Queue (DLQ) for Failed Events" "M5" "reliability,tooling" \
"**Context**
Persist permanently failed events, add CLI to inspect/replay.

**Acceptance Criteria**
- DLQ schema with payload, error, retries, ts
- Failures captured with request_id
- CLI: list/view/replay
- Docs for safe replay"

# ---------------- M6 ----------------
create_issue \
"Create Deployment Documentation and Local Smoke Test" "M6" "docs" \
"**Context**
Expand README with setup/run instructions.

**Acceptance Criteria**
- Env vars/scopes documented
- Run locally + ngrok instructions validated by new dev
- Smoke test creates GitHub issue
- Screenshots/asciinema optional"

# ---------------- M7 ----------------
create_issue \
"Implement Multi-Project/Repo Routing" "M7" "enhancement,config" \
"**Context**
Route events to different repos by Linear team/label/project.

**Acceptance Criteria**
- ROUTING_RULES_JSON schema validated
- Resolver picks correct repo, fallback exists
- Unit tests cover precedence cases
- Routing decision logs present"

create_issue \
"Add Content Checksum to Avoid No-Op Updates" "M7" "performance" \
"**Context**
Use SHA256 checksum of title/body to avoid no-op patches.

**Acceptance Criteria**
- Checksum column populated
- Handler short-circuits on unchanged content
- Logs show no-op reason
- Tests verify no PATCH sent"

# ---------------- Backlog ----------------
create_issue \
"Backfill Utility (Linear → GitHub for existing issues)" "" "tooling,backlog" \
"**Context**
Batch create GitHub issues for existing Linear issues.

**Acceptance Criteria**
- Dry-run mode prints actions
- Batching respects rate limits
- Skips already mapped issues
- Progress + error reporting clear"

create_issue \
"Optional Bi-Directional Sync (GitHub → Linear) behind feature flag" "" "research,backlog" \
"**Context**
Experimental reverse mirroring.

**Acceptance Criteria**
- Feature-flagged off by default
- Scoped to safe fields
- Audit logs kept
- Risks documented"

create_issue \
"Role-Based Admin Endpoints (read-only status, mapping export)" "" "observability,backlog" \
"**Context**
Add ops endpoints and export.

**Acceptance Criteria**
- Status endpoints for health/stats
- AuthZ/IP allowlist
- CSV/JSON export
- Ops workflow documented"

say "Done."
