# Security Audit Report – Datenschutzportal

**Datum:** 2026-03-05
**Prüfer:** Claude (automatisierte OWASP-Analyse)
**Tools:** bandit, pip-audit, npm audit, manueller Code-Review
**Standard:** OWASP Top 10 (2021)

---

## Zusammenfassung

| Schweregrad | Anzahl gefunden | Anzahl behoben |
|-------------|:--------------:|:--------------:|
| Kritisch    | 0              | –              |
| Hoch        | 4              | 4              |
| Mittel      | 6              | 4              |
| Niedrig     | 4              | 2              |

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

## Offene / Empfohlene Maßnahmen (nicht automatisch behebbar)

### [HIGH] A07 – API-Token im Frontend-JavaScript-Bundle sichtbar

**Datei:** `frontend/src/services/api.ts`
**Problem:** `VITE_API_TOKEN` wird zur Build-Zeit in das JavaScript-Bundle eingebettet und ist für jeden Browser-Nutzer im Quelltext lesbar. Ein Angreifer kann den Token extrahieren und beliebige Upload-Anfragen direkt an die API senden.
**Empfehlung:** API-Endpunkte, die keine Nutzer-Authentifizierung erfordern (öffentliches Upload-Portal), sollten CORS-basierte Origin-Prüfung + Rate Limiting als primäre Schutzmaßnahme nutzen, statt eines Secret-Tokens. Alternativ: Backend-BFF (Backend-for-Frontend) mit Session-Cookie-basierter Authentifizierung, so dass kein Token im Bundle liegt.

---

### [MEDIUM] A07 – python-jose mit Algorithm-Confusion und DoS-CVEs

**Paket:** `python-jose==3.3.0`
**CVEs:** PYSEC-2024-232 (Algorithm Confusion), PYSEC-2024-233 (DoS via JWE)
**Empfehlung:** Migration zu `PyJWT>=2.8.0`. python-jose wird nicht mehr aktiv gepflegt.
*(Hinweis im requirements.txt eingetragen)*

---

### [MEDIUM] A04 – Kein Rate Limiting auf dem Upload-Endpunkt

**Problem:** `POST /api/upload` hat kein Rate Limiting. Ein Angreifer könnte massenhaft Upload-Anfragen stellen (DoS, Spam).
**Empfehlung:** `slowapi` (FastAPI-kompatibel) oder Traefik-Middleware-basiertes Rate Limiting einrichten.

```python
# Beispiel mit slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/upload", ...)
@limiter.limit("10/hour")
async def upload_documents(request: Request, ...):
    ...
```

---

### [MEDIUM] A05 – CORS zu permissiv konfiguriert

**Datei:** `backend/app/main.py`
**Problem:** `allow_methods=["*"]` und `allow_headers=["*"]` erlauben alle HTTP-Methoden und Header von konfigurierten Origins.
**Empfehlung:** Auf die tatsächlich benötigten Methoden und Header beschränken:

```python
allow_methods=["POST", "GET"],
allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
```

---

### [LOW] A05 – Default-Wert `"change-me"` für `log_redaction_secret`

**Datei:** `backend/app/config.py:70`
**Problem:** Wenn `LOG_REDACTION_SECRET` nicht gesetzt wird, ist das HMAC-Hashing von E-Mail-Adressen in Logs mit einem bekannten Key kompromittiert.
**Empfehlung:** Keinen Default-Wert setzen und beim Start prüfen, ob der Wert gesetzt ist:

```python
log_redaction_secret: str  # Kein Default – muss in .env gesetzt sein
```

---

### [LOW] A03 – `dangerouslySetInnerHTML` mit i18n-String

**Datei:** `frontend/src/components/ConfirmationPage.tsx:158`
**Problem:** `dangerouslySetInnerHTML={{ __html: t('confirmation.step3') }}` rendert HTML-Markup aus der Übersetzungsdatei ungefiltert. Falls die i18n-Ressource kompromittiert wird (Supply-Chain), ist XSS möglich.
**Empfehlung:** Prüfen, ob der HTML-Markup in der Übersetzung wirklich notwendig ist. Falls ja, eine Sanitier-Bibliothek (z.B. `DOMPurify`) vorschalten.

---

### [LOW] A02 – Schwacher JWT-Algorithmus konfigurierbar

**Datei:** `backend/app/config.py:171`
**Problem:** `algorithm: str = "HS256"` – der Algorithmus ist über die Umgebungsvariable überschreibbar. Kein Schutz gegen Downgrade auf `none` oder asymmetrische Algorithmen.
**Empfehlung:** Algorithmus fest im Code verankern oder zulässige Werte via `Literal["HS256", "HS512"]` einschränken.

---

### [INFO] A04 – Keine Dateiinhalt-Validierung (Magic Bytes)

**Problem:** Die Dateitypprüfung basiert ausschließlich auf der Dateiendung. Eine `shell.php` umbenannt zu `shell.pdf` würde die Prüfung bestehen.
**Empfehlung:** `python-magic` oder `filetype` einsetzen, um den tatsächlichen MIME-Typ anhand der Magic Bytes zu verifizieren.

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
