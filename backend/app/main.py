from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import upload, projects, health
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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(health.router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {"message": "Datenschutzportal API", "version": "1.0.0"}
