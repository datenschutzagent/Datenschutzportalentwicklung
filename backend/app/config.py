from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    EnvSettingsSource,
    DotEnvSettingsSource,
)
from pydantic import field_validator
from typing import List, Literal, Any
import json
from pathlib import Path


def _find_env_file() -> str | None:
    """
    Find a .env file by walking upwards from the current working directory.
    This keeps a single source of truth (.env in project root) while also
    working in Docker where the app is typically run from /app.
    """
    try:
        start = Path.cwd().resolve()
    except Exception:
        start = Path(".").resolve()

    for p in [start, *start.parents]:
        candidate = p / ".env"
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None

class _LenientEnvSettingsSource(EnvSettingsSource):
    def decode_complex_value(self, field_name: str, field: Any, value: str) -> Any:
        try:
            return json.loads(value)
        except Exception:
            return value


class _LenientDotenvSettingsSource(DotEnvSettingsSource):
    def decode_complex_value(self, field_name: str, field: Any, value: str) -> Any:
        try:
            return json.loads(value)
        except Exception:
            return value

class Settings(BaseSettings):
    # Allow unrelated env vars (e.g. TZ/LOG_LEVEL/VITE_*) without crashing.
    model_config = SettingsConfigDict(env_file=_find_env_file(), extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            _LenientEnvSettingsSource(settings_cls),
            _LenientDotenvSettingsSource(settings_cls),
            file_secret_settings,
        )

    # Logging
    log_level: str = "INFO"
    env: str = "dev"
    service_name: str = "datenschutzportal-backend"
    # Used for HMAC hashing of PII (e.g. email_hash) in logs.
    # No default – must be set via environment variable (OWASP A02 / CWE-798).
    log_redaction_secret: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> Any:
        """
        Accept both JSON arrays and comma-separated strings, e.g.
        - CORS_ORIGINS='["https://ds.niceai.de","http://localhost:3000"]'
        - CORS_ORIGINS='https://ds.niceai.de,http://localhost:3000'
        """
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    # Fall back to comma-separated parsing
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    @field_validator("notification_emails", mode="before")
    @classmethod
    def _parse_notification_emails(cls, v: Any) -> Any:
        """
        Accept both JSON arrays and comma-separated strings, e.g.
        - NOTIFICATION_EMAILS='["team1@example.com","team2@example.com"]'
        - NOTIFICATION_EMAILS=team1@example.com,team2@example.com
        """
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def _parse_allowed_file_types(cls, v: Any) -> Any:
        """
        Accept both JSON arrays and comma-separated strings, e.g.
        - ALLOWED_FILE_TYPES='[".pdf",".docx",".zip"]'
        - ALLOWED_FILE_TYPES=.pdf,.docx,.zip
        """
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v
    
    # Nextcloud
    nextcloud_url: str
    nextcloud_username: str
    nextcloud_password: str
    nextcloud_base_path: str = "/Datenschutzportal"
    
    # SMTP
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str = "Datenschutzportal"
    smtp_encryption: Literal["starttls", "ssl", "none"] = "starttls"
    
    # Notifications
    notification_emails: List[str]
    
    # Security
    secret_key: str
    api_token: str
    # algorithm is only used for signing upload session tokens; HS256 is the only accepted value.
    algorithm: Literal["HS256"] = "HS256"
    # Lifetime in seconds for short-lived upload session tokens issued by /api/upload-token
    upload_token_ttl_seconds: int = 300  # 5 minutes
    
    # File Upload
    max_file_size: int = 52428800  # 50 MB
    allowed_file_types: List[str] = [
        ".pdf",
        ".doc",
        ".docx",
        ".zip",
        ".odt",
        ".ods",
        ".odp",
        ".png",
        ".jpg",
        ".jpeg",
        ".xlsx",
        ".csv",
        ".odf",
    ]

settings = Settings()
