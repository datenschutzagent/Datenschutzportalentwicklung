# Backend Setup & Integration

## Übersicht

Das Backend wird mit **Python FastAPI** entwickelt und bietet REST-API-Endpunkte für den Upload, Projektmanagement und E-Mail-Benachrichtigungen.

## Technologie-Stack

### Core
- **Python**: 3.11+
- **FastAPI**: 0.115+
- **Uvicorn**: ASGI Server
- **Pydantic / Pydantic-Settings**: Data Validation & Konfiguration

### Datei-Speicherung
- **WebDAV Client**: Nextcloud Integration (`webdavclient3`)

### E-Mail
- **SMTP**: `aiosmtplib` (async)
- **Jinja2**: E-Mail Templates

### Authentifizierung & Sicherheit
- **PyJWT**: Kurz-lebige Upload-Session-Tokens
- **slowapi**: Rate Limiting (OWASP A04)
- **filetype**: Magic-Bytes-Validierung bei Datei-Uploads (OWASP A01)
- **passlib[bcrypt]**: Passwort-Hashing

### Logging
- **structlog**: Strukturiertes JSON-Logging
- **orjson**: Hochperformante JSON-Serialisierung

## Projektstruktur (Backend)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI App, Middleware-Registrierung
│   ├── config.py               # Pydantic-Settings Konfiguration
│   ├── limiter.py              # slowapi Rate-Limiter Instanz
│   ├── logging_config.py       # structlog Konfiguration
│   ├── middleware/
│   │   ├── request_context.py  # X-Request-ID Correlation
│   │   └── security_headers.py # HTTP-Sicherheits-Header
│   ├── models/
│   │   ├── project.py          # Pydantic Models
│   │   └── upload.py
│   ├── routes/
│   │   ├── upload.py           # POST /api/upload
│   │   ├── token.py            # GET /api/upload-token
│   │   ├── projects.py         # GET /api/
│   │   └── health.py           # GET /api/health
│   ├── services/
│   │   ├── nextcloud.py        # WebDAV Integration
│   │   ├── email_service.py    # E-Mail Versand
│   │   └── validation.py       # Business Logic
│   ├── utils/
│   │   ├── auth.py             # Token-Verifikation (hmac.compare_digest)
│   │   └── helpers.py
│   └── templates/
│       ├── base.html
│       ├── email_confirmation_de.html
│       └── email_confirmation_en.html
├── tests/
│   ├── test_upload.py
│   └── test_nextcloud.py
├── requirements.txt
├── Dockerfile
└── Dockerfile.dev
```

## Installation

### 1. Python Environment

```bash
# Python Virtual Environment erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### 2. Requirements.txt

```txt
# --- Security-patched versions (see SECURITY.md) ---
fastapi>=0.115.0
uvicorn[standard]>=0.27.0
# python-multipart >=0.0.22 fixes CVE-2026-24486 und CVE-2024-53981
python-multipart>=0.0.22
pydantic>=2.9.0
pydantic-settings>=2.5.0
structlog==25.5.0
orjson==3.11.5
webdavclient3==3.14.6
# jinja2 >=3.1.6 fixes mehrere CVEs
jinja2>=3.1.6
aiosmtplib==3.0.1
sqlalchemy==2.0.25
alembic==1.13.1
# python-jose entfernt (PYSEC-2024-232/233 – DoS + Algorithm Confusion)
# PyJWT ist der aktiv gewartete Ersatz für Upload-Session-Tokens
PyJWT>=2.8.0
passlib[bcrypt]==1.7.4
pytest==7.4.4
pytest-asyncio==0.23.3
httpx>=0.27.0
python-dotenv==1.0.0
email-validator==2.1.0
# Rate Limiting (OWASP A04 – Insecure Design)
slowapi>=0.1.9
# Magic-Bytes-Validierung (OWASP A01 / CWE-434 – Unrestricted File Upload)
filetype>=1.2.0
```

## Konfiguration

### .env Datei

Die `.env`-Datei liegt im **Projekt-Root** (nicht im `backend/`-Verzeichnis) und dient als Single Source of Truth für Backend und Frontend-Build.

```env
# Logging (strukturierte JSON-Logs auf stdout)
LOG_LEVEL=INFO
ENV=prod
SERVICE_NAME=datenschutzportal-backend
# HMAC-Secret für PII-Redaction in Logs (z.B. email_hash) – Pflichtfeld, kein Default
LOG_REDACTION_SECRET=change-me-in-production

# API Konfiguration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
# JSON-Array oder CSV-String
CORS_ORIGINS=["https://your-frontend-domain.com","http://localhost:3000"]

# Nextcloud Konfiguration
NEXTCLOUD_URL=https://nextcloud.example.com/remote.php/webdav/
NEXTCLOUD_USERNAME=your_username
NEXTCLOUD_PASSWORD=your_password
NEXTCLOUD_BASE_PATH=/Datenschutzportal

# SMTP Konfiguration
SMTP_HOST=smtp.uni-frankfurt.de
SMTP_PORT=587
SMTP_USERNAME=your_email@uni-frankfurt.de
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=ForschungFB16@uni-frankfurt.de
SMTP_FROM_NAME=Datenschutzportal
# Verschlüsselung: "starttls" (default) | "ssl" | "none"
SMTP_ENCRYPTION=starttls

# Benachrichtigungs-E-Mails (JSON-Array oder CSV)
NOTIFICATION_EMAILS=team1@uni-frankfurt.de,team2@uni-frankfurt.de

# Sicherheit
SECRET_KEY=your-secret-key-here-change-in-production
API_TOKEN=your-secret-token
# Gültigkeitsdauer des Upload-JWT in Sekunden (default: 300 = 5 Minuten)
UPLOAD_TOKEN_TTL_SECONDS=300

# Datei-Upload
MAX_FILE_SIZE=52428800  # 50 MB in Bytes
ALLOWED_FILE_TYPES=.pdf,.doc,.docx,.odt,.ods,.odp,.zip,.png,.jpg,.jpeg,.xlsx,.csv,.odf

# Frontend Build-Variablen (werden zur Build-Zeit eingebettet)
VITE_API_URL=https://api.example.com/api
VITE_API_TOKEN=your-secret-token  # muss mit API_TOKEN übereinstimmen

# Traefik (Produktion)
FRONTEND_HOST=portal.example.com
BACKEND_HOST=api.example.com
TRAEFIK_ACME_EMAIL=admin@example.com
```

### Konfigurationsfelder (config.py)

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `log_level` | str | `"INFO"` | Log-Level |
| `env` | str | `"dev"` | Umgebung (dev/prod) |
| `service_name` | str | `"datenschutzportal-backend"` | Service-Name in Logs |
| `log_redaction_secret` | str | — (Pflicht) | HMAC-Secret für PII-Redaktion |
| `api_host` | str | `"0.0.0.0"` | Bind-Adresse |
| `api_port` | int | `8000` | Bind-Port |
| `api_debug` | bool | `False` | Debug-Modus |
| `cors_origins` | List[str] | localhost-Defaults | Erlaubte CORS-Ursprünge |
| `nextcloud_url` | str | — (Pflicht) | WebDAV-URL |
| `nextcloud_username` | str | — (Pflicht) | Nextcloud-Benutzername |
| `nextcloud_password` | str | — (Pflicht) | Nextcloud-Passwort |
| `nextcloud_base_path` | str | `"/Datenschutzportal"` | Basis-Pfad in Nextcloud |
| `smtp_host` | str | — (Pflicht) | SMTP-Server |
| `smtp_port` | int | `587` | SMTP-Port |
| `smtp_username` | str | — (Pflicht) | SMTP-Benutzername |
| `smtp_password` | str | — (Pflicht) | SMTP-Passwort |
| `smtp_from_email` | str | — (Pflicht) | Absender-E-Mail |
| `smtp_from_name` | str | `"Datenschutzportal"` | Absender-Name |
| `smtp_encryption` | Literal | `"starttls"` | TLS-Modus: starttls / ssl / none |
| `notification_emails` | List[str] | — (Pflicht) | Benachrichtigungs-Empfänger |
| `secret_key` | str | — (Pflicht) | Secret für JWT-Signierung |
| `api_token` | str | — (Pflicht) | Statischer API-Token |
| `algorithm` | Literal["HS256"] | `"HS256"` | JWT-Signierungsalgorithmus |
| `upload_token_ttl_seconds` | int | `300` | JWT-Gültigkeitsdauer (Sekunden) |
| `max_file_size` | int | `52428800` | Max. Dateigröße (Bytes) |
| `allowed_file_types` | List[str] | Liste gängiger Formate | Erlaubte Dateiendungen |

## Middleware

Das Backend registriert zwei Middlewares in `main.py`:

### SecurityHeadersMiddleware
Setzt HTTP-Sicherheits-Header auf alle Antworten (OWASP A05):

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`

### RequestContextMiddleware
Propagiert `X-Request-ID` für strukturiertes Logging und Anfrage-Korrelation. Generiert eine neue ID, wenn keine im Request vorhanden ist.

## Lokale Entwicklung

```bash
# Backend direkt starten
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Oder via Docker Compose (empfohlen)
docker compose -f docker-compose.dev.yml up -d --build
```

## Tests ausführen

```bash
cd backend
pytest
pytest --cov=app tests/
```

## Deployment

Siehe [Deployment Guide](../deployment/index.md) für die vollständige Deployment-Anleitung.

## Status

| Schritt | Status |
|---------|--------|
| Python Environment & Requirements | Erledigt |
| API-Endpunkte implementiert | Erledigt |
| E-Mail-Templates (DE/EN) | Erledigt |
| Nextcloud WebDAV-Integration | Erledigt |
| SMTP-Service | Erledigt |
| Middleware (Security Headers, Request Context) | Erledigt |
| Rate Limiting (slowapi) | Erledigt |
| Docker-Deployment | Erledigt |
| OWASP-Sicherheitsaudit | Erledigt |
| Integration Tests erweitern | Offen |
| Admin-Dashboard | Offen |
