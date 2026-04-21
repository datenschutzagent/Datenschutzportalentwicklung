# Tech Stack Dokumentation

## Frontend-Technologien

### Core Framework

#### React (TypeScript)
- **Version**: 18.3+
- **Verwendung**: Haupt-Framework für die UI
- **Vorteile**:
  - Komponentenbasierte Architektur
  - TypeScript für Type Safety
  - Große Community & Ecosystem

### Styling

#### Tailwind CSS
- **Version**: 4.0
- **Verwendung**: Utility-First CSS Framework
- **Konfiguration**: `src/styles/globals.css`
- **Features**:
  - CSS Custom Properties für Theming
  - Responsive Design Utilities

#### Class Variance Authority (CVA)
- **Version**: 0.7.1
- **Verwendung**: Variant-basierte Komponenten-Styles

### UI-Komponenten

#### Radix UI
- **Verwendung**: Headless UI Primitives (vollständig barrierefrei – ARIA)
- **Genutzte Komponenten**: Dialog, Popover, Select, Accordion, Checkbox, Radio Group u.a.

#### shadcn/ui
Alle UI-Komponenten unter `src/components/ui/` basieren auf shadcn/ui (Radix UI + Tailwind).

### Icons

#### Lucide React
- **Version**: 0.487+
- **Verwendung**: Icon Library

### Form Handling

#### React Hook Form
- **Version**: 7.55+
- **Verwendung**: Formular-Management und Validierung
- **Vorteile**: Performance (uncontrolled components), eingebaute Validierung

### Weitere Libraries

| Library | Version | Verwendung |
|---------|---------|-----------|
| Recharts | 2.15+ | Datenvisualisierung |
| Sonner | 2.0+ | Toast Notifications |
| Vaul | — | Drawer Component |
| React Day Picker | — | Datepicker |
| Embla Carousel | — | Karussell-Komponente |

## Backend-Technologien

### Core Framework

#### FastAPI
- **Version**: 0.115+
- **Verwendung**: REST-API Backend
- **Features**: Async/Await, automatische OpenAPI-Dokumentation, Pydantic-Integration

#### Uvicorn
- **Verwendung**: ASGI Server (Standard-Worker)

#### Pydantic / Pydantic-Settings
- **Version**: 2.9+ / 2.5+
- **Verwendung**: Datenvalidierung & typsichere Konfigurationsverwaltung

### Datei-Speicherung

#### webdavclient3
- **Version**: 3.14.6
- **Verwendung**: Nextcloud WebDAV-Integration
- **Operationen**: Upload, Ordner erstellen, Metadaten speichern

### E-Mail

#### aiosmtplib
- **Version**: 3.0.1
- **Verwendung**: Asynchroner SMTP-Client für Bestätigungs- und Team-E-Mails

#### Jinja2
- **Version**: 3.1.6+
- **Verwendung**: HTML-E-Mail-Templates (DE/EN)

### Authentifizierung & Sicherheit

#### PyJWT
- **Version**: 2.8+
- **Verwendung**: Kurz-lebige Upload-Session-Tokens (JWT, HS256)
- **Hinweis**: Ersetzt `python-jose`, das aufgrund von CVEs (PYSEC-2024-232/233) entfernt wurde

#### passlib[bcrypt]
- **Version**: 1.7.4
- **Verwendung**: Passwort-Hashing

#### slowapi
- **Version**: 0.1.9+
- **Verwendung**: Rate Limiting (OWASP A04 – Insecure Design)
- **Konfiguration**: 10 Req/Std für `/api/upload`, 30 Req/Std für `/api/upload-token`

#### filetype
- **Version**: 1.2.0+
- **Verwendung**: Magic-Bytes-Validierung bei Datei-Uploads (OWASP A01 / CWE-434)
- **Zweck**: Prüft tatsächlichen Dateiinhalt statt nur Dateiendung

### Logging

#### structlog
- **Version**: 25.5.0
- **Verwendung**: Strukturiertes JSON-Logging

#### orjson
- **Version**: 3.11.5
- **Verwendung**: Hochperformante JSON-Serialisierung (für structlog)

### Datenbank (optional, derzeit nicht aktiv)

- **SQLAlchemy 2.0**: ORM (installiert, primär Nextcloud als Storage)
- **Alembic 1.13**: Migrationen

### Test

| Library | Version | Verwendung |
|---------|---------|-----------|
| pytest | 7.4.4 | Test-Framework |
| pytest-asyncio | 0.23.3 | Async-Test-Support |
| httpx | 0.27+ | HTTP-Client für API-Tests |

## Build Tools

### Vite
- **Version**: 6.3+
- **Verwendung**: Frontend Build Tool & Dev Server
- **Features**: Extrem schnelles HMR, optimierte Produktions-Builds

## Sicherheits-Architektur

### HTTP-Sicherheits-Header (SecurityHeadersMiddleware)

Alle API-Antworten enthalten folgende Header:

| Header | Wert |
|--------|------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Cache-Control` | `no-store` |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` |

### Token-Exchange-Flow

Der statische `API_TOKEN` (im Frontend-Bundle eingebettet) wird nie direkt für Upload-Operationen verwendet. Stattdessen wird ein kurz-lebiger JWT (Standard: 5 Minuten) über `GET /api/upload-token` ausgetauscht. Siehe [API Dokumentation](../backend/api.md).

### Rate Limiting (slowapi)

Schützt vor Missbrauch und Brute-Force-Angriffen:
- `POST /api/upload`: 10 Anfragen/Stunde pro IP
- `GET /api/upload-token`: 30 Anfragen/Stunde pro IP

### Datei-Upload-Sicherheit

1. **Magic-Bytes-Prüfung** (`filetype`): Dateiinhalt wird unabhängig von der Dateiendung validiert
2. **Filename-Sanitierung**: Path-Traversal-Angriffe werden durch `os.path.basename()` und Sonderzeichen-Ersatz verhindert
3. **Dateigrößen-Limit**: Konfigurierbar via `MAX_FILE_SIZE` (Standard: 50 MB)
4. **Dateiendungs-Allowlist**: Nur explizit erlaubte Formate werden akzeptiert

### Timing-sicherer Token-Vergleich

Token-Vergleiche nutzen `hmac.compare_digest()` statt `==`/`!=`, um Timing-Angriffe (CWE-208) zu verhindern.

### PII-Redaktion in Logs

E-Mail-Adressen und andere personenbezogene Daten werden in Logs als HMAC-Hash gespeichert (`LOG_REDACTION_SECRET`). Klartext-PII erscheint nie in Logs.

### OWASP-Compliance

Alle im Sicherheitsaudit (März 2026) identifizierten Schwachstellen wurden behoben. Vollständige Details: `SECURITY.md` im Projekt-Root und [Sicherheitsdokumentation](../security.md).
