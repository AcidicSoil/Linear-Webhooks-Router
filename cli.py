from __future__ import annotations

import argparse
import json
import os
import httpx

from app.config import get_settings
from app.db.repository import MappingRepository


def cmd_list(repo: MappingRepository, args):
    for row in repo.dlq_list():
        print(f"{row['id']:>4}  {row['event_type']:<16} retries={row['retries']} last_seen={row['last_seen']}")


def cmd_view(repo: MappingRepository, args):
    row = repo.dlq_get(args.id)
    if not row:
        print("not found")
        return
    print(json.dumps(row, indent=2))


def cmd_replay(repo: MappingRepository, args):
    row = repo.dlq_get(args.id)
    if not row:
        print("not found")
        return
    url = args.url or "http://127.0.0.1:8000/linear/webhook"
    payload = row["payload"]
    try:
        r = httpx.post(url, content=payload, timeout=15.0)
        print(r.status_code, r.text)
        if r.status_code < 300:
            repo.dlq_delete(args.id)
        else:
            repo.dlq_bump_retry(args.id, f"HTTP {r.status_code}")
    except Exception as exc:
        repo.dlq_bump_retry(args.id, str(exc))
        print("replay failed:", exc)


def main():
    parser = argparse.ArgumentParser(prog="dlq")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)

    p_view = sub.add_parser("view")
    p_view.add_argument("id", type=int)
    p_view.set_defaults(func=cmd_view)

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("id", type=int)
    p_replay.add_argument("--url")
    p_replay.set_defaults(func=cmd_replay)

    args = parser.parse_args()
    settings = get_settings()
    repo = MappingRepository(settings.db_url())
    args.func(repo, args)


if __name__ == "__main__":
    main()

