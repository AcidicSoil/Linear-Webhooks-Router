import argparse
import hmac
import hashlib
import json
import os
import sys
import httpx


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Send a signed Linear webhook to local server")
    parser.add_argument("--url", default="http://127.0.0.1:8000/linear/webhook")
    parser.add_argument("--secret", default=os.getenv("LINEAR_WEBHOOK_SECRET", "devsecret"))
    parser.add_argument("--event", choices=["issue.create", "issue.update", "issue.close", "comment.create"], default="issue.create")
    args = parser.parse_args()

    if args.event == "issue.create":
        payload = {
            "type": "Issue",
            "action": "create",
            "data": {"id": "DEV-1", "title": "Smoke Test", "description": "created from smoke test"},
        }
    elif args.event == "issue.update":
        payload = {
            "type": "Issue",
            "action": "update",
            "data": {"id": "DEV-1", "title": "Smoke Test Updated", "description": "updated body"},
        }
    elif args.event == "issue.close":
        payload = {"type": "Issue", "action": "close", "data": {"id": "DEV-1", "state": {"name": "Done"}}}
    else:
        payload = {"type": "Comment", "action": "create", "data": {"issueId": "DEV-1", "user": {"name": "Tester"}, "body": "hi"}}

    body = json.dumps(payload).encode()
    headers = {"linear-signature": sign(body, args.secret)}
    r = httpx.post(args.url, content=body, headers=headers, timeout=10.0)
    print(r.status_code, r.text)


if __name__ == "__main__":
    main()

