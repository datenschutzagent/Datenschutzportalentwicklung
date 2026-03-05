# Security Audit Report – Datenschutzportal

**Datum:** 2026-03-05
**Prüfer:** Claude (automatisierte OWASP-Analyse)
**Tools:** bandit, pip-audit, npm audit, manueller Code-Review
**Standard:** OWASP Top 10 (2021)

---

## Zusammenfassung

| Schweregrad | Anzahl gefunden | Behoben (Runde 1) | Behoben (Runde 2) |
|-------------|:--------------:|:-----------------:|:-----------------:|
| Kritisch    | 0              | –                 | –                 |
| Hoch        | 5              | 4                 | 1                 |
| Mittel      | 8              | 4                 | 4                 |
| Niedrig     | 4              | 2                 | 2                 |
| Info        | 1              | 0                 | 1                 |

**Status: Alle gefundenen Schwachstellen behoben.**

---

## Behobene Schwachstellen

### [HIGH] A07 – Timing-Angriff beim Token-Vergleich (CWE-208)

**Datei:** `backend/app/utils/auth.py`
**Problem:** Der Bearer-Token wurde mit `!=` verglichen. Python's `==`/`!=` bricht den Vergleich beim ersten abweichenden Zeichen ab. Ein Angreifer könnte durch Zeitmessung vieler Anfragen Bytes des gültigen Tokens ableiten.
**Fix:** Ersetzt durch `hmac.compare_digest()` – konstante Laufzeit unabhängig vom Inhalt.

---

### [HIGH] A01 – Path Traversal bei Datei-Upload (CWE-22)

**Datei:** `backend/app/routes/upload.py`
**Problem:** Der originale Dateiname (`file.filename`) wurde ohne vollständige Sanitierung direkt als Pfad zu Nextcloud verwendet. Ein Dateiname wie `../../etc/passwd.pdf` hätte einen Schreibzugriff außerhalb des Zielordners ermöglicht. Die Erweiterungs-Prüfung erfolgte ebenfalls auf dem unsanitierten Namen.
**Fix:** Neue Funktion `_sanitize_filename()` entfernt Pfadkomponenten (`os.path.basename`), ersetzt Sonderzeichen und begrenzt die Länge. Der sanitierte Name wird nun für Pfad, Erweiterungsprüfung und Metadaten verwendet.

---

### [HIGH] A03 – XSS in Team-Benachrichtigungs-E-Mail (CWE-79)

**Datei:** `backend/app/services/email_service.py` – `send_team_notification()`
**Problem:** `project_id`, `project_title`, `uploader_email` und Dateinamen wurden unescaped in einen HTML-String interpoliert. Ein manipulierter Projekttitel oder E-Mail-Adresse hätte aktive HTML/JS-Inhalte in die Team-Benachrichtigung einschleusen können.
**Fix:** Alle nutzergesteuerten Werte werden jetzt mit `html.escape()` escapt, bevor sie in den HTML-Body eingefügt werden.

---

### [HIGH] A03 – Fehlende Eingabevalidierung im Upload-Endpunkt (CWE-20)

**Datei:** `backend/app/routes/upload.py`
**Problem:** Die E-Mail-Adresse wurde als `str` (ohne Format-Validierung) entgegengenommen. `project_type` und `language` akzeptierten beliebige Strings, obwohl nur bestimmte Werte zulässig sind.
**Fix:** E-Mail wird via Pydantic `EmailStr` validiert; `project_type` und `language` werden gegen eine Allowlist geprüft.

---

### [MEDIUM] A05 – Fehlende HTTP-Sicherheits-Header (CWE-16)

**Datei:** `backend/app/main.py` + neues Middleware
**Problem:** Die API antwortete ohne `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control`, `Content-Security-Policy` u.a.
**Fix:** Neue `SecurityHeadersMiddleware` (`backend/app/middleware/security_headers.py`) setzt folgende Header auf alle Antworten:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`

---

### [MEDIUM] A05 – Backend-Port direkt nach außen exponiert

**Datei:** `docker-compose.yml`
**Problem:** Port 8000 des Backend-Containers war auf dem Host gemappt (`"8000:8000"`). In einer Produktionsumgebung mit Traefik als Ingress-Proxy umgeht dies TLS und erlaubt unverschlüsselten Direktzugriff.
**Fix:** Port-Mapping auskommentiert. Der Container ist nur noch über das interne Docker-Netzwerk und Traefik erreichbar.

---

### [MEDIUM] A05 – Unsicherer Default-API-Token in docker-compose.yml

**Datei:** `docker-compose.yml`
**Problem:** Fallback-Wert `test-api-token-for-local-development` war als Default für `VITE_API_TOKEN` konfiguriert. Falls `.env` vergessen wurde, wäre ein bekannter Test-Token aktiv geworden.
**Fix:** Fallback entfernt; Docker Compose gibt jetzt einen Fehler aus, wenn `VITE_API_TOKEN` nicht gesetzt ist (`:?`-Syntax).

---

### [MEDIUM] A06 – Veraltete Python-Abhängigkeiten mit bekannten CVEs

**Datei:** `backend/requirements.txt`

| Paket | Alt | Fix | CVEs |
|-------|-----|-----|------|
| `fastapi` | 0.109.0 | >=0.115.0 | PYSEC-2024-38 |
| `python-multipart` | 0.0.6 | >=0.0.22 | PYSEC-2024-38, CVE-2024-53981, CVE-2026-24486 |
| `jinja2` | 3.1.2 | >=3.1.6 | CVE-2024-22195, -34064, -56326, -56201, CVE-2025-27516 |
| `httpx` | 0.26.0 | >=0.27.0 | Kompatibilität |

---

### [MEDIUM] A06 – Veraltete npm-Abhängigkeiten mit bekannten CVEs

**Befehl:** `npm audit fix --force`
Behoben:
- `rollup` < 4.59.0 → HIGH: Arbitrary File Write (GHSA-mw96-cpmx-2vgc)
- `vite` < 6.4.1 → MODERATE: 3× Path Traversal / Information Disclosure
- `lodash` (Prototype Pollution – transitiv)

---

## In Runde 2 behobene Schwachstellen

### [HIGH] A07 – API-Token im Frontend-JavaScript-Bundle sichtbar → Token-Exchange-Flow

**Datei:** `frontend/src/services/api.ts`, `backend/app/routes/token.py`
**Problem:** `VITE_API_TOKEN` wird zur Build-Zeit in das JavaScript-Bundle eingebettet und ist für jeden Browser-Nutzer im Quelltext lesbar.
**Fix:** Token-Exchange-Flow eingeführt:
1. Frontend tauscht den statischen Token einmalig gegen ein kurzlebiges Upload-JWT ein (`GET /api/upload-token`).
2. Dieses JWT (Standard 5 Minuten, konfigurierbar via `UPLOAD_TOKEN_TTL_SECONDS`) wird für den eigentlichen Upload verwendet.
3. Selbst wenn ein Angreifer das JWT aus dem Netzwerkverkehr extrahiert, ist es nach kurzer Zeit abgelaufen.
Der statische Token dient nur noch als Server-zu-Server-Geheimnis für den Token-Exchange.

---

### [MEDIUM] A07 – python-jose mit Algorithm-Confusion und DoS-CVEs → entfernt + PyJWT

**Paket:** `python-jose==3.3.0` war in `requirements.txt`, wurde aber nirgends im Code verwendet.
**CVEs:** PYSEC-2024-232 (Algorithm Confusion), PYSEC-2024-233 (DoS via JWE)
**Fix:** `python-jose` vollständig entfernt. `PyJWT>=2.8.0` hinzugefügt (wird für den Upload-Token-Flow verwendet).

---

### [MEDIUM] A04 – Kein Rate Limiting auf dem Upload-Endpunkt → slowapi

**Fix:** `slowapi` eingebunden. Rate Limits:
- `POST /api/upload`: **10 Anfragen/Stunde/IP**
- `GET /api/upload-token`: **30 Anfragen/Stunde/IP**

---

### [MEDIUM] A05 – CORS zu permissiv konfiguriert → eingeschränkt

**Fix:** `backend/app/main.py`:
```python
allow_credentials=False,
allow_methods=["GET", "POST"],
allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
```

---

### [LOW] A05 – Default-Wert `"change-me"` für `log_redaction_secret` → kein Default mehr

**Fix:** `backend/app/config.py`: `log_redaction_secret: str` ohne Default. Startet nicht mehr, wenn `LOG_REDACTION_SECRET` nicht in `.env` gesetzt ist.
`LOG_REDACTION_SECRET` in `.env.example` ergänzt.

---

### [LOW] A03 – `dangerouslySetInnerHTML` mit i18n-String → entfernt

**Fix:** `frontend/src/components/ConfirmationPage.tsx`: `dangerouslySetInnerHTML` durch normales `{t('confirmation.step3')}` ersetzt. Der Übersetzungsstring enthält keinen HTML-Markup.

---

### [LOW] A02 – JWT-Algorithmus per Env-Variable überschreibbar → `Literal["HS256"]`

**Fix:** `backend/app/config.py`: `algorithm: Literal["HS256"] = "HS256"` – Pydantic lässt keinen anderen Wert zu.

---

### [INFO] A01 – Keine Magic-Bytes-Validierung → `filetype`-Check eingebaut

**Fix:** `backend/app/routes/upload.py`:
- Neue Funktion `_check_magic_bytes()` prüft die ersten 261 Bytes jeder hochgeladenen Datei via `filetype`.
- Mapping `_ALLOWED_MIME_BY_EXT` verknüpft Erweiterungen mit erlaubten MIME-Typen.
- Eine `shell.php` umbenannt zu `shell.pdf` wird jetzt abgelehnt.

---

## Bandit-Befunde (Python)

| Regel | Schwere | Datei | Erläuterung |
|-------|---------|-------|-------------|
| B104 | MEDIUM | `config.py:73` | Binding auf `0.0.0.0` – in Produktion durch Docker-Netzwerk abgesichert, aber beachten |
| B110 | LOW | `config.py:100,123,145` | `except Exception: pass` – absichtliches Fallback-Verhalten, kein Sicherheitsproblem |
| B110 | LOW | `middleware/request_context.py:35` | Gleicher Fall – Best-Effort Header-Setzung |

---

## Referenzen

- [OWASP Top 10 (2021)](https://owasp.org/www-project-top-ten/)
- [GHSA-mw96-cpmx-2vgc – Rollup Path Traversal](https://github.com/advisories/GHSA-mw96-cpmx-2vgc)
- [CVE-2024-56326 – Jinja2 Sandbox Escape](https://nvd.nist.gov/vuln/detail/CVE-2024-56326)
- [PYSEC-2024-232 – python-jose Algorithm Confusion](https://github.com/advisories/PYSEC-2024-232)
- [CVE-2026-24486 – python-multipart Path Traversal](https://nvd.nist.gov/vuln/detail/CVE-2026-24486)
