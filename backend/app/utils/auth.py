from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings
import hmac
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Accept either:
      1. The static API token (server-to-server, e.g. /api/upload-token endpoint).
      2. A short-lived upload JWT issued by /api/upload-token (frontend uploads).

    Uses constant-time comparison for the static token to prevent timing attacks (CWE-208).
    """
    token = credentials.credentials
    logger.debug("Token verification requested")

    # --- Path 1: static API token (constant-time compare to prevent CWE-208) ---
    if hmac.compare_digest(token.encode(), settings.api_token.encode()):
        logger.debug("Static API token accepted")
        return token

    # --- Path 2: short-lived upload JWT ---
    # Import here to avoid circular dependency (token module imports verify_token)
    try:
        from app.routes.token import verify_upload_token
        if verify_upload_token(token):
            logger.debug("Upload JWT accepted")
            return token
    except Exception:
        pass  # fall through to 401

    logger.warning(f"Invalid token provided (token length: {len(token) if token else 0})")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
