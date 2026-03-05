from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings
import hmac
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the Bearer Token using constant-time comparison to prevent timing attacks.
    """
    token = credentials.credentials
    logger.debug("Token verification requested")

    # Use hmac.compare_digest to prevent timing side-channel attacks (CWE-208)
    if not hmac.compare_digest(token.encode(), settings.api_token.encode()):
        logger.warning(f"Invalid token provided (token length: {len(token) if token else 0})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Token verified successfully")
    return token
