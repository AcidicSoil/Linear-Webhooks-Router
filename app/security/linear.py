import hmac
import hashlib
from typing import Optional

from fastapi import Depends, HTTPException, Request

from ..config import Settings, get_settings


def compute_linear_signature(body: bytes, secret: str) -> str:
    """Return hex-encoded HMAC-SHA256 signature for Linear webhook body.

    Linear’s signature is a lowercase hex digest of HMAC-SHA256 over the raw
    request body, using the shared webhook secret.
    """
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def verify_linear_signature(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    """FastAPI dependency to verify Linear webhook signature.

    Expects header: 'linear-signature' containing the hex digest. Reads the raw
    request body and compares in constant time. Raises an HTTPException on
    failure to stop request processing.
    """
    provided: Optional[str] = request.headers.get("linear-signature")
    if not provided:
        raise HTTPException(status_code=400, detail="missing linear-signature header")

    body = await request.body()
    expected = compute_linear_signature(body, settings.linear_webhook_secret)

    # Normalize header value (should be hex); compare in constant time
    if not hmac.compare_digest(expected, provided.strip().lower()):
        raise HTTPException(status_code=403, detail="invalid signature")

