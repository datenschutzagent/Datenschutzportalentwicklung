# CLAUDE.md – Datenschutzportal

This file provides context for AI assistants working on this codebase.

## Project Overview

**Datenschutzportal** is a full-stack web application for secure submission of data protection documents for research projects at the University of Frankfurt and the University Hospital Frankfurt (UKF).

- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS 4.0
- **Backend**: Python FastAPI + Uvicorn
- **Storage**: Nextcloud (WebDAV)
- **Email**: SMTP via aiosmtplib
- **Deployment**: Docker Compose + Traefik (Let's Encrypt TLS)
- **Documentation**: MkDocs with Material theme (source in `mkdocs/`, built to `docs/`)

## Key Entry Points

| Component | Path |
|-----------|------|
| Frontend app root | `frontend/src/App.tsx` |
| Main wizard component | `frontend/src/components/DataProtectionPortal.tsx` |
| Backend app | `backend/app/main.py` |
| Backend config | `backend/app/config.py` |
| API routes | `backend/app/routes/` |
| Services | `backend/app/services/` |
| Email templates | `backend/app/templates/` |
| Docker (production) | `docker-compose.yml` |
| Docker (development) | `docker-compose.dev.yml` |
| Environment template | `env.example` |
| MkDocs source | `mkdocs/` |

## Development Environment

```bash
# Start everything with hot reload
docker compose -f docker-compose.dev.yml up -d --build

# Frontend only (http://localhost:3000)
cd frontend && npm install && npm run dev

# Backend only (http://localhost:8000)
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Build documentation
pip install -r requirements.txt  # project root
mkdocs build
mkdocs serve  # preview at http://localhost:8000
```

## Architecture

### Frontend Workflow (multi-step wizard)
1. Institution selection (`InstitutionSelection`)
2. Project type selection (`ProjectTypeSelection`)
3. File upload form (`FileUploadSection` / `ExistingProjectForm`)
4. Confirmation page (`ConfirmationPage`)

State is managed by the `useDataProtectionWorkflow` custom hook. i18n via `LanguageContext` (DE/EN, 230+ keys).

### Backend API Flow
1. Frontend calls `GET /api/upload-token` with static `VITE_API_TOKEN` → receives short-lived JWT
2. Frontend calls `POST /api/upload` with JWT → backend validates, uploads to Nextcloud, sends emails

### Configuration
Single `.env` file at project root is the source of truth. `VITE_*` variables are embedded into the frontend bundle at build time.

## Coding Standards

### Language Convention
- **Source code** (variables, functions, comments): **English**
- **MkDocs documentation** (`mkdocs/` folder): **German**
- **Git commit messages**: English (Conventional Commits)

### Commit Message Format
```
<type>(<scope>): <subject>
```
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

### TypeScript / React
- Functional components, no class components
- Custom hooks for logic separation (prefix: `use`)
- `interface` for object types, not `type`
- No `any`; use `unknown` and narrow explicitly
- Destructure props; early return pattern for guards

### Python / FastAPI
- Type hints on all public functions
- PEP 8 style
- `snake_case` for functions/variables, `PascalCase` for classes
- No bare `except:`; catch specific exceptions

### CSS / Tailwind
- No `position: absolute` unless strictly necessary
- Class order: layout → spacing → typography → colors → effects
- Mobile-first responsive design

## Security Notes

- **Never log PII in plaintext** – email addresses are HMAC-hashed via `LOG_REDACTION_SECRET`
- **Token comparison** must use `hmac.compare_digest()`, not `==`
- **File uploads**: always sanitize filenames and validate magic bytes
- **HTML in emails**: always escape user input with `html.escape()`
- **No secrets in code**: use environment variables only
- Rate limits: `/api/upload` 10/hr, `/api/upload-token` 30/hr per IP
- Full security details: `SECURITY.md` and `mkdocs/security.md`

## Testing

```bash
# Backend tests
cd backend
pytest
pytest --cov=app tests/

# Frontend (no test suite configured yet)
cd frontend
npm run build  # verify build succeeds
```

## Documentation

Documentation source is in `mkdocs/` (Markdown). Build with `mkdocs build` → output goes to `docs/`.

Do not edit files in `docs/` directly – they are generated.

MkDocs navigation is defined in `mkdocs.yml`.
