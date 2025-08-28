# Linear → GitHub Webhook Bridge

## Overview

A lightweight FastAPI service that synchronizes Linear issues and comments with GitHub issues. It ensures updates in Linear are mirrored to GitHub, maintaining a consistent backlog across platforms.

## Features

* ✅ Verify Linear webhook signatures for security
* ✅ Create, update, and close GitHub issues based on Linear events
* ✅ Mirror Linear comments to GitHub issue comments
* ✅ Maintain idempotency with a mapping database (Linear issue ↔ GitHub issue)
* ✅ Configurable for single or multiple projects
* ✅ Ready for deployment on Vercel, Fly, or any VM

## Tech Stack

* **Python 3.11+**
* **FastAPI** – Web server framework
* **Uvicorn** – ASGI server
* **httpx** – HTTP client for GitHub API requests
* **SQLite** (or Redis/KV store in production) – Mapping storage

## Installation (with uv)

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/linear-github-bridge.git
   cd linear-github-bridge
   ```

2. Create and activate a virtual environment (uv):

   ```bash
   uv venv
   # POSIX
   source .venv/bin/activate
   # Windows PowerShell
   # .venv\Scripts\Activate.ps1
   ```

3. Install dependencies (uv):

   ```bash
   uv pip install -r requirements.txt
   ```

4. Set environment variables:

   ```bash
   export GITHUB_OWNER=acme
   export GITHUB_REPO=my-repo
   export GITHUB_TOKEN=ghp_xxx              # needs "repo" scope
   export LINEAR_WEBHOOK_SECRET=lin_wh_...  # from Linear UI
   ```

## Usage

### Run locally

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

Expose your service publicly (e.g., with [ngrok](https://ngrok.com/)):

```bash
ngrok http 8000
```

Paste the public URL into **Linear → Settings → API → Webhooks**.

### Smoke test (without Linear)

```bash
body='{"type":"Issue","action":"create","data":{"id":"123","identifier":"LIN-123","title":"Example from Linear","description":"Details...","url":"https://linear.app/...","state":{"type":"triage"}}}'
sig=$(uv run python - <<'PY'
import os, hmac, hashlib, sys
secret=os.environ["LINEAR_WEBHOOK_SECRET"].encode()
raw=open(0,'rb').read()
print(hmac.new(secret, raw, hashlib.sha256).hexdigest())
PY
<<< "$body")
curl -i -H "linear-signature: $sig" -H "content-type: application/json" \
  --data "$body" http://localhost:8000/linear/webhook
```

This should create a corresponding GitHub issue labeled `source:linear`.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-update`)
3. Commit changes with clear messages
4. Open a pull request describing your changes

## License

MIT License

# Linear Webhooks Router

FastAPI service that receives Linear webhooks and mirrors issue and comment events to GitHub. Includes signature verification, SQLite mapping store, GitHub API client with retries, event routing, and structured JSON logging.

## Requirements

* Python 3.11+
* `uv` (recommended) or `pip`

## Setup with uv

```bash
uv venv
uv pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
```

Required environment variables:

* `GITHUB_OWNER` – target org/user
* `GITHUB_REPO` – target repo
* `GITHUB_TOKEN` – PAT with repo scope
* `LINEAR_WEBHOOK_SECRET` – shared secret used to sign Linear webhooks
* `LOG_LEVEL` – default `INFO`
* `STORAGE_URL` – optional SQLite path; default `data/app.db`

## Run locally

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expose locally via ngrok (optional):

```bash
ngrok http http://localhost:8000
```

## Smoke test

Send a signed payload to the local server. By default uses `LINEAR_WEBHOOK_SECRET` from env (or `devsecret`).

```bash
uv run python scripts/smoke_test.py --event issue.create
```

Other events:

```bash
uv run python scripts/smoke_test.py --event issue.update
uv run python scripts/smoke_test.py --event issue.close
uv run python scripts/smoke_test.py --event comment.create
```

## Running tests

```bash
uv run pytest -q
```

## Deployment

* Build container with Python 3.11 base, copy project, install requirements, run `uvicorn app.main:app`. Ensure env vars are provided and persistent storage mapped if using file DB.
