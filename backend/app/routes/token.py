"""
Short-lived upload session token endpoint.

Rationale (OWASP A07 – Identification and Authentication Failures):
The static VITE_API_TOKEN embedded in the frontend JS bundle is visible to any
user who inspects the source.  This endpoint issues a short-lived JWT (default
5 min) signed with SECRET_KEY, so the upload route can validate it without
exposing a long-lived secret in the bundle.

Flow:
  1. Frontend loads → calls GET /api/upload-token with the static API token in
     the Authorization header.
  2. Backend verifies the static token (server-to-server secret) and returns a
     short-lived JWT.
  3. Frontend uses that JWT for the actual POST /api/upload call.

The static API token never needs to be used for upload directly; it is only
used once to obtain the upload token.  Rate limiting on this endpoint prevents
token-farming.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request
import jwt

from app.config import settings
from app.limiter import limiter
from app.utils.auth import verify_token

router = APIRouter()


def create_upload_token() -> str:
    """Issue a short-lived JWT granting permission to perform one upload batch."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "datenschutzportal",
        "aud": "upload",
        "iat": now,
        "exp": now + timedelta(seconds=settings.upload_token_ttl_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_upload_token(token: str) -> bool:
    """
    Validate an upload session token.
    Returns True if valid, False otherwise.
    """
    try:
        jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience="upload",
        )
        return True
    except jwt.PyJWTError:
        return False


@router.get(
    "/upload-token",
    summary="Issue a short-lived upload token",
    dependencies=[Depends(verify_token)],
)
@limiter.limit("30/hour")
async def get_upload_token(request: Request):
    """
    Exchange the static API token for a short-lived upload JWT.
    Rate-limited to 30 requests per IP per hour.
    """
    token = create_upload_token()
    return {
        "token": token,
        "expires_in": settings.upload_token_ttl_seconds,
    }
