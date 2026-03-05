from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.config import settings
from app.routes import upload, projects, health, token as token_route
from app.logging_config import configure_logging
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
import structlog

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Datenschutzportal API",
    description="API für Datenschutz-Dokument Upload",
    version="1.0.0"
)

# Rate limiter – keyed by client IP (OWASP A04 – Insecure Design)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def _startup() -> None:
    # Uvicorn configures logging after importing the app. We (re-)apply our structlog
    # configuration on startup to ensure uvicorn.* and app logs are JSON.
    configure_logging(
        service_name=settings.service_name,
        env=settings.env,
        log_level="DEBUG" if settings.api_debug else settings.log_level,
    )
    logger.info("api_start")

# Security headers (OWASP A05 – Security Misconfiguration)
app.add_middleware(SecurityHeadersMiddleware)

# Request context / correlation
app.add_middleware(RequestContextMiddleware)

# CORS Middleware – restrict to the minimum required (OWASP A05)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # No cookies/credentials used; keeps CORS safe
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Routes
app.include_router(token_route.router, prefix="/api", tags=["auth"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(health.router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {"message": "Datenschutzportal API", "version": "1.0.0"}
