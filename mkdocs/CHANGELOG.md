# Changelog

Alle wichtigen Änderungen am Datenschutzportal werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geplant
- Admin-Dashboard (Upload-Übersicht, Projekt-Verwaltung)
- CI/CD Pipeline (GitHub Actions)
- Virus-Scanning (ClamAV)
- Kubernetes-Manifeste
- Prometheus Metrics / Grafana Dashboards

## [2.1.0] - 2026-03-05

### Sicherheit (OWASP-Audit – Runde 1 & 2)

Vollständiger OWASP-Top-10-Audit mit Behebung aller gefundenen Schwachstellen.

#### [HIGH] Timing-Angriff beim Token-Vergleich (CWE-208)
- Token-Vergleich auf `hmac.compare_digest()` umgestellt (konstante Laufzeit)

#### [HIGH] Path Traversal bei Datei-Upload (CWE-22)
- Neue Funktion `_sanitize_filename()` bereinigt Pfadkomponenten (`os.path.basename`),
  ersetzt Sonderzeichen und begrenzt Dateinamen-Länge

#### [HIGH] XSS in Team-Benachrichtigungs-E-Mail (CWE-79)
- Alle nutzergesteuerten Werte in HTML-E-Mails werden mit `html.escape()` escapt

#### [HIGH] Fehlende Eingabevalidierung im Upload-Endpunkt (CWE-20)
- E-Mail via Pydantic `EmailStr` validiert
- `project_type` und `language` gegen Allowlist geprüft

#### [MEDIUM] Fehlende HTTP-Sicherheits-Header (CWE-16)
- Neue `SecurityHeadersMiddleware` setzt: `X-Content-Type-Options`, `X-Frame-Options`,
  `X-XSS-Protection`, `Referrer-Policy`, `Cache-Control`, `Content-Security-Policy`

#### [MEDIUM] Backend-Port nach außen exponiert
- Port-Mapping in `docker-compose.yml` entfernt; Backend nur noch intern erreichbar

#### [MEDIUM] Unsicherer Default-API-Token
- Kein Fallback-Token mehr; fehlende Konfiguration führt zu Startfehler

#### [MEDIUM] Veraltete Abhängigkeiten mit bekannten CVEs
- `fastapi`, `python-multipart`, `jinja2`, `rollup`, `vite` auf sichere Versionen aktualisiert
- `python-jose` (PYSEC-2024-232/233) entfernt und durch `PyJWT>=2.8.0` ersetzt

#### [MEDIUM] API-Token im JavaScript-Bundle
- Kurz-lebiger JWT-Token-Exchange-Flow implementiert:
  `GET /api/upload-token` tauscht statischen Token gegen 5-Minuten-JWT

#### [MEDIUM] Fehlende Rate Limiting
- `slowapi` integriert: 10 Req/Std für `/api/upload`, 30 Req/Std für `/api/upload-token`

#### [LOW] CORS zu permissiv
- CORS auf spezifische Methoden (GET, POST) und Header beschränkt

#### [LOW] Unsichere JWT-Algorithmus-Konfiguration
- `algorithm`-Feld auf `Literal["HS256"]` (Pydantic) eingeschränkt

#### [INFO] Magic-Bytes-Validierung
- `filetype`-Bibliothek prüft tatsächlichen Dateiinhalt statt nur Dateiendung

## [2.0.0] - 2026-01-01

### Hinzugefügt

#### Backend-Integration
- FastAPI REST-Backend mit Uvicorn ASGI-Server
- Nextcloud WebDAV-Integration (`webdavclient3`):
  - Automatische Ordnerstruktur pro Projekt und Kategorie
  - Upload von `metadata.json` und `README.md` pro Projekt
- E-Mail-Service mit `aiosmtplib` und Jinja2-Templates:
  - Bestätigungs-E-Mail an Einreicher (DE/EN)
  - Benachrichtigung an das Datenschutz-Team
- Strukturiertes JSON-Logging (`structlog` + `orjson`)
- Request-Correlation via `X-Request-ID`-Header
- Pydantic-basierte Konfigurationsverwaltung (`pydantic-settings`)

#### API-Endpunkte
- `POST /api/upload` – Dokument-Upload mit Nextcloud-Speicherung und E-Mail
- `GET /api/upload/status/{project_id}` – Upload-Status und Metadaten
- `GET /api/upload-token` – Kurz-lebiger JWT für Upload-Authentifizierung
- `GET /api/` – Projektliste (Platzhalter)
- `GET /api/health` – Health-Check

#### Deployment
- Docker Compose für Produktion mit Traefik-Reverse-Proxy und Let's Encrypt TLS
- Docker Compose für Entwicklung mit Hot-Reload
- Zentrale `.env`-Datei als Single Source of Truth

#### Middleware
- `RequestContextMiddleware`: Correlation-ID-Propagierung
- `SecurityHeadersMiddleware`: HTTP-Sicherheits-Header

## [1.0.0] - 2024-12-12

### Hinzugefügt

#### Workflow & Navigation
- Mehrstufiger Workflow mit Institution-Auswahl
- Projekt-Typ-Auswahl (neu/bestehend)
- Zurück-Navigation zwischen Steps
- Breadcrumb-Navigation (visuell)
- Bestätigungsseite mit Upload-Details

#### Dokumenten-Upload
- 7 kategorisierte Upload-Bereiche:
  - Datenschutzkonzept (Pflicht)
  - Übernahme der Verantwortung (Pflicht)
  - Schulung Uni Nachweis (Pflicht)
  - Schulung UKF Nachweis (Pflicht)
  - Einwilligung (bedingt Pflicht)
  - Ethikvotum (optional)
  - Sonstiges (optional)
- Drag & Drop Upload-Funktion
- Multi-File Support pro Kategorie
- Dateiliste mit Größenangabe
- Datei-Entfernen-Funktion
- Upload-Fortschrittsanzeige (0-100%)
- PDF-Vorschau mit Zoom (50%-200%)

#### Formular & Validierung
- E-Mail-Validierung (RegEx)
- Projekttitel (Pflichtfeld)
- Uploader-Name (optional)
- Prospektive Studie Checkbox
- Conditional Required Fields (Einwilligung)
- Echtzeit-Fehleranzeige
- Warning-System für optionale Felder
- Client-seitige Validierung

#### Internationalisierung
- Vollständige DE/EN Übersetzung (230+ Keys)
- Sprachwechsel-Button
- Context-basiertes i18n System
- Alle UI-Elemente übersetzt
- Fehler- und Erfolgsmeldungen übersetzt

#### UI/UX
- Responsive Design (Mobile/Tablet/Desktop)
- Moderne UI mit Tailwind CSS 4.0
- shadcn/ui Komponenten
- Radix UI für Accessibility
- Lucide React Icons
- Hover-Effekte und Transitions
- Loading States / Error States / Success States

#### Komponenten
- `DataProtectionPortal` (Hauptkomponente)
- `InstitutionSelection`
- `ProjectTypeSelection`
- `ExistingProjectForm`
- `FileUploadSection`
- `UploadProgress`
- `PDFPreview`
- `ConfirmationPage`
- `LanguageSwitch`
- 30+ wiederverwendbare UI-Komponenten

#### Dokumentation
- MkDocs-Dokumentationssite mit Material-Theme
- Backend-Setup, API, Frontend-Architektur, Deployment, Tech Stack, Contributing

### Technische Details

#### Frontend Stack
- React 18.3 mit TypeScript
- Tailwind CSS 4.0
- Radix UI 1.1.2+
- Class Variance Authority 0.7.1
- Lucide React Icons
- Context API für State Management

#### Code-Qualität
- TypeScript Strict Mode
- Functional Components
- Custom Hooks
- Component Composition Pattern
- Type-Safe Props

## [0.1.0] - 2024-12-01

### Hinzugefügt
- Projekt-Initialisierung
- Basis-Struktur
- Erste Komponenten-Prototypen

---

## Support & Kontakt

**Datenschutz-Team**: ForschungFB16@uni-frankfurt.de
