# Sicherheits- und CI/CD-Analyse – Datenschutzportal

**Datum:** 2026-09-05
**Stand:** `main` @ `0402c6b`
**Methode:** manueller Code-Review (Backend, Frontend, Docker/Traefik), praktische Verifikation gegen die laufende App (httpx/ASGI), `pytest`, `pip-audit`, `bandit`, `npm audit`, `npm run build`, Git-History-Scan, GitHub-API (Workflows, PRs, Dependabot).

**Rahmenbedingung:** Das Fehlen einer Nutzer-Authentifizierung ist eine bewusste Designentscheidung und wird hier nicht als Befund gewertet. Daraus folgt aber: Der einzige "Schutz" der API ist der im Frontend-Bundle eingebettete `VITE_API_TOKEN`, und der ist öffentlich. Alle Befunde sind unter dieser Prämisse zu lesen: **Jeder im Internet kann jeden Endpunkt aufrufen.**

---

## 1. Zusammenfassung

| # | Schwere | Befund | Bereich |
|---|---------|--------|---------|
| 1 | **Hoch** | Rate Limiting wirkt global statt pro IP (Uvicorn vertraut `X-Forwarded-For` von Traefik nicht) → 10 Uploads/h für **alle** Nutzer zusammen; triviales DoS | Deployment / Backend |
| 2 | **Hoch** | `GET /api/upload/status/{project_id}` gibt Metadaten (E-Mail, Name, Projektdetails) **beliebiger** Einreichungen preis; IDs sind erratbar | Backend |
| 3 | **Hoch** | Keine Begrenzung der Request-Gesamtgröße/Dateianzahl; Größenprüfung erst nach vollständigem Empfang → Disk-/RAM-Erschöpfung | Backend / Traefik |
| 4 | **Hoch** | Keine CI/CD-Pipeline, kein Dependabot, PRs werden ohne Review innerhalb von Minuten gemerged | Prozess |
| 5 | **Mittel** | Verwundbare Abhängigkeiten: `aiosmtplib 3.0.1` (2 Advisories), `orjson 3.11.5`, `vite 6.4.1` + 4 transitive npm-HIGH | Dependencies |
| 6 | **Mittel** | Projektordner kollidieren (gleicher Titel + Tag) → Dateien/Metadaten anderer Einreicher werden überschrieben bzw. vermischt | Backend |
| 7 | **Mittel** | Fehlermeldungen leaken interne Details (Nextcloud-URL + Service-User, interner Basispfad, rohe Exception-Texte) | Backend |
| 8 | **Mittel** | Keinerlei Längen-/Wertebegrenzung für `project_title`, `project_details`, `uploader_name`, `institution` (5000-Zeichen-Titel wird akzeptiert) | Backend |
| 9 | **Mittel** | Portal ist ein offener E-Mail-Versender: Bestätigungsmail mit angreifer-kontrolliertem Betreff/Inhalt an beliebige Adresse im Namen der Universität | Design |
| 10 | **Mittel** | Blockierende, synchrone WebDAV-I/O im async-Handler → ein langsamer Upload blockiert den gesamten Server | Backend |
| 11 | **Mittel** | Token-Exchange-Flow ist wirkungslos: statischer Token wird direkt auf `/upload` akzeptiert, JWT kann neue JWTs ausstellen; Doku stellt ihn als "HIGH behoben" dar | Backend / Doku |
| 12 | **Mittel** | Kein HSTS, keine CSP für das Frontend, nginx-Header-Vererbungsfehler, Frontend-Port 3000 am Host vorbei an Traefik/TLS exponiert | Deployment |
| 13 | **Mittel** | Backend-Image läuft als root, enthält `gcc`, Docs-/Test-/DB-Pakete; Prod-Compose mountet Quellcode; `.dockerignore` ist per `.gitignore` verboten | Deployment |
| 14 | **Niedrig** | Dokumentation widersprüchlich/veraltet (Magic-Bytes-Prüfung wird in `CLAUDE.md` und `mkdocs/security.md` behauptet, ist aber entfernt) | Doku |
| 15 | **Niedrig** | `/docs`, `/redoc`, `/openapi.json` öffentlich; `X-Request-ID` ungeprüft übernommen; PII kann über SMTP-Fehlertexte in Logs gelangen | Backend |
| 16 | **Niedrig** | `letsencrypt/` (ACME-Private-Keys) nicht in `.gitignore`; `docs/` ist getrackt aber ignoriert; Traefik-Loglevel DEBUG als Default | Deployment |
| 17 | **Niedrig** | Keine Mindestlänge für `SECRET_KEY`/`API_TOKEN`; Python-Deps ohne Lockfile/Hashes; npm-Wildcards (`clsx: "*"`) | Konfiguration |

**Positiv:** Filename-Sanitizing ist solide, HTML-Escaping in Mails korrekt (Jinja-Autoescape + `html.escape`), `hmac.compare_digest`, PII-Hashing in Logs, CORS restriktiv, kein `dangerouslySetInnerHTML`, keine Secrets in der Git-History, Tests laufen (8 passed), Build läuft.

---

## 2. Backend – Details

### 2.1 [HOCH] Rate Limiting ist global, nicht pro IP

`backend/app/limiter.py` nutzt `get_remote_address` → `request.client.host`. Der Uvicorn-Default ist `--forwarded-allow-ips 127.0.0.1` (verifiziert: `Config().forwarded_allow_ips == "127.0.0.1"`). Traefik spricht das Backend über das Docker-Netz (172.x) an, also wird `X-Forwarded-For` **nicht** übernommen und jede Anfrage trägt die Traefik-IP.

Folgen:
- `10/hour` auf `/api/upload` gilt für alle Nutzer der Plattform zusammen. Ab dem 11. Upload am Tag ist das Portal für eine Stunde für alle dicht.
- Ein Angreifer schickt 10 leere Mini-Uploads und hat die Plattform für eine Stunde abgeschaltet; 30 Requests auf `/upload-token` reichen ebenso.
- Gleichzeitig ist der beabsichtigte Schutz (Missbrauch pro Angreifer begrenzen) faktisch nicht vorhanden, da alle im selben Topf landen.

Fix:
- Uvicorn mit `--proxy-headers --forwarded-allow-ips=<Traefik-Container-IP oder Subnetz>` starten (`backend/Dockerfile` CMD). `*` nur, wenn das Backend garantiert nicht direkt erreichbar ist (aktuell hängt es auch im `datenschutzportal-network` mit dem Frontend-Container).
- Alternativ Rate Limiting in Traefik (`ratelimit`-Middleware) machen, dort ist die Client-IP bekannt.
- In-Memory-Storage von slowapi ist bei einem Restart oder mehreren Replikas nutzlos; für eine Instanz akzeptabel, dokumentieren.

### 2.2 [HOCH] Informationsleck über `GET /api/upload/status/{project_id}`

`backend/app/routes/upload.py:292`. Verifiziert: Mit einem per Frontend-Token geholten JWT liefert der Endpunkt `metadata.json` (E-Mail, Name, Projektdetails, Dateinamen) eines beliebigen Projekts. Die Projekt-ID ist `<Titel>_<YYYY-MM-DD>` bzw. `RE_<Titel>_<Datum>`, also aus Titel und Datum erratbar oder aus einer Bestätigungsmail bekannt.

Das Frontend benutzt den Endpunkt nicht. Fix: Endpunkt entfernen. Falls er gebraucht wird: zufällige, nicht ableitbare IDs (z. B. `secrets.token_urlsafe(16)`) und ausschließlich in der Bestätigungsmail an den Einreicher ausgeben.

### 2.3 [HOCH] Keine Begrenzung der Gesamt-Request-Größe

- `max_file_size` (50 MB) wird pro Datei geprüft, es gibt kein Limit für die Anzahl der Dateien und keins für den Body insgesamt.
- Starlette parst den kompletten Multipart-Body, bevor der Handler läuft. Die 50-MB-Prüfung greift also **nach** dem vollständigen Empfang; Dateien werden bis dahin in Temp-Dateien gespoolt.
- `nextcloud.upload_file` liest zusätzlich jede Datei komplett in den RAM (`await file.read()`) und schreibt sie erneut in eine Temp-Datei.
- Weder Traefik noch Uvicorn setzen ein Body-Limit.

Fix: Traefik-Middleware `buffering.maxRequestBodyBytes` (z. B. 300 MB) auf dem Backend-Router; im Handler `len(files)` begrenzen (z. B. ≤ 20); Datei in Chunks in die Temp-Datei streamen statt `read()`.

### 2.4 [MITTEL] Ordner-Kollisionen zwischen Einreichern

`project_id = f"{safe_title}_{date_str}"`. Zwei Einreichungen mit demselben (sanitisierten) Titel am selben Tag landen im selben Nextcloud-Ordner; `metadata.json` und `README.md` werden überschrieben, gleichnamige Dateien ebenso. Nebeneffekt: Umlaute werden gelöscht ("Über Ärzte" → `ber_rzte_2026-09-05`, verifiziert), ein rein nicht-lateinischer Titel wird zu `_2026-09-05`. Kollisionen sind damit wahrscheinlicher als es aussieht, und ein Angreifer kann eine bekannte Einreichung gezielt überschreiben.

Fix: ID mit Zufallsanteil (`<safe_title>_<date>_<6 hex>`), Ordner nur anlegen wenn nicht vorhanden (`client.check` → 409), Titel mit `unicodedata.normalize("NFKD")` transliterieren.

### 2.5 [MITTEL] Fehlerdetails an den Client

Verifiziert:
- 503: `"... Error: Failed to connect to Nextcloud: 401 Unauthorized for https://cloud.internal/remote.php/dav/files/svc_user"` → interne URL und Service-Account-Name.
- 500 bei `create_folder`: enthält `project_path` inkl. `NEXTCLOUD_BASE_PATH`.
- 500-Fallback: `f"Internal server error: {str(e)}"` → beliebige Exception-Texte, z. B. `'list' object has no attribute 'get'` wenn `file_categories` ein JSON-Array ist.

Fix: generische Fehlermeldungen nach außen, Details nur ins Log (mit `request_id`, die der Client ja bekommt).

### 2.6 [MITTEL] Fehlende Eingabegrenzen

Akzeptiert (verifiziert): `project_title` mit 5000 Zeichen, `institution="<script>"`. Kein Limit für `project_details`, `uploader_name`. `file_categories` wird als beliebiges JSON übernommen; Werte (auch verschachtelte Objekte) landen in Metadaten, README und E-Mail. `is_prospective_study`/`institution` werden nicht gegen eine Allowlist geprüft, obwohl `models/upload.py::ProjectSubmission` genau das definiert – das Modell wird nur nirgends benutzt.

Fix: `Form(..., max_length=200)` für Titel, `max_length=5000` für Details, `institution` gegen `("university", "clinic")`, `file_categories` als `Dict[str, Literal[...]]` per Pydantic validieren; toten Code (`models/upload.py::ProjectSubmission`, `services/validation.py`, `utils/helpers.py`, `routes/projects.py`) entfernen oder benutzen.

### 2.7 [MITTEL] Offener E-Mail-Versand mit Fremdinhalt

`send_confirmation_email` geht an die frei eingegebene Adresse, Betreff und Anrede enthalten `project_title`/`uploader_name` ungefiltert. Ergebnis: Jeder kann im Namen der Universität (gültige SPF/DKIM-Absenderdomain) Mails mit beliebigem Betreff an Dritte auslösen. Header-Injection per CRLF ist **nicht** möglich (Pythons `email`-Paket faltet/encodiert den Betreff, verifiziert), aber Phishing-Text im Betreff schon.

Ohne Nutzer-Auth lässt sich das nur abmildern:
- Titel im Betreff kürzen (z. B. 80 Zeichen) und Steuerzeichen entfernen; besser: Betreff ohne Freitext ("Bestätigung Ihrer Einreichung [ID]").
- Rate Limit muss real pro IP wirken (2.1).
- Optional ein Bot-Schutz (Cloudflare Turnstile/hCaptcha) vor `/upload-token` – das ist keine Nutzer-Auth und passt zum Designziel.
- Optional Double-Opt-in: Upload erst nach Klick auf Bestätigungslink. Ist die einzige Maßnahme, die Fremdadressen wirklich schützt.

### 2.8 [MITTEL] Blockierende I/O im Event-Loop

`webdavclient3` ist synchron; `test_connection`, `create_folder`, `upload_sync`, `download_sync` werden direkt in `async def`-Handlern aufgerufen. Während ein 50-MB-Upload zur Nextcloud läuft, bearbeitet der Worker keine andere Anfrage, auch `/api/health` nicht → Healthcheck-Flapping und Verstärkung von 2.3.

Fix: Aufrufe in `await asyncio.to_thread(...)` bzw. `run_in_executor` verpacken oder einen async WebDAV-Client (httpx direkt) einsetzen.

### 2.9 [MITTEL] Token-Exchange-Flow bringt keinen Sicherheitsgewinn

Verifiziert:
- Der statische Token wird direkt auf `POST /api/upload` akzeptiert (`verify_token` prüft beides).
- Ein JWT wird auf `GET /api/upload-token` akzeptiert und stellt ein neues JWT aus (Kette ohne Ende).
- Der statische Token ist im Bundle und damit öffentlich; ein 5-Minuten-JWT, das jeder jederzeit kostenlos bekommt, schützt nichts.

Das ist kein Bug im engeren Sinn, aber `SECURITY.md` verkauft es als behobene HIGH-Schwachstelle. Empfehlung: Ehrlich dokumentieren, dass die API absichtlich offen ist und die Schutzmaßnahmen Rate Limiting, Validierung, Body-Limits und ggf. Bot-Schutz sind. Falls der Flow bleibt: `/upload` nur JWT, `/upload-token` nur statischer Token, `jti` + Einmalverwendung.

### 2.10 [NIEDRIG] Kleinere Punkte

- `/docs`, `/redoc`, `/openapi.json` sind öffentlich (FastAPI-Default). In Prod `docs_url=None, redoc_url=None, openapi_url=None`.
- `X-Request-ID` wird ungeprüft übernommen (Länge, Zeichensatz) und landet in jeder Logzeile → Log-Injection/Aufblähen. Auf z. B. `^[A-Za-z0-9_-]{1,64}$` prüfen, sonst neue UUID.
- `email_send_failed` loggt `error_message=str(e)`; SMTP-Fehler enthalten oft die Empfängeradresse (`550 5.1.1 <user@x> ...`) → PII im Log entgegen der Redaction-Policy.
- `project_id` (= Projekttitel) wird überall ungehasht geloggt, während `project_title` auf der Redact-Liste steht. Inkonsistent.
- `SECRET_KEY`/`API_TOKEN` haben keine Mindestlänge; PyJWT warnt bei < 32 Bytes. `env.example` liefert `change-me-in-production` – ein Validator (`min_length=32`, nicht in einer Blacklist) verhindert Prod-Starts mit Platzhaltern.
- `@app.on_event("startup")` ist deprecated → Lifespan.
- `smtp_encryption="none"` sollte außerhalb von `ENV=dev` verweigert werden.
- `datetime.now()` ohne TZ; für Ordnernamen und Mails `ZoneInfo("Europe/Berlin")` explizit nutzen.

---

## 3. Frontend

- Kein XSS-Vektor gefunden: kein `dangerouslySetInnerHTML`, keine `innerHTML`, PDF-Vorschau über `URL.createObjectURL` in `<object>` (Browser-Sandbox).
- Der statische Token liegt zwangsläufig im Bundle; das ist bekannt und akzeptiert.
- **Kein Typecheck, kein Lint:** `typescript` und `eslint` fehlen in den devDependencies, `tsc` wird nie ausgeführt; Vite/SWC strippt Typen nur. Die `@ts-expect-error`-Kommentare sind damit wirkungslos. `npm run build` ist der einzige "Test".
- Wildcard-Versionen `clsx: "*"`, `tailwind-merge: "*"` → nicht reproduzierbar ohne Lockfile-Disziplin.
- Kein clientseitiges Größenlimit vor dem Upload (UX, kein Sicherheitsproblem).
- `index.html` hat `lang="en"` für eine primär deutsche Seite; kein `<meta http-equiv="Content-Security-Policy">` – CSP gehört aber ohnehin in nginx/Traefik (siehe 4.3).
- ~27 Radix-Pakete werden installiert, das Bundle ist mit 214 kB klein → Tree-Shaking funktioniert, aber die Supply-Chain-Fläche (npm audit, Dependabot-Rauschen) ist unnötig groß. Ungenutzte `components/ui/*` und Pakete entfernen.

---

## 4. Deployment (Docker / Traefik / nginx)

### 4.1 [MITTEL] Frontend am Host exponiert
`docker-compose.yml` mappt `3000:80` für das Frontend. Damit ist das Portal unverschlüsselt auf Port 3000 erreichbar, an Traefik vorbei. Der Kommentar beim Backend ("Traefik acts as the sole ingress") gilt für das Frontend nicht. Mapping entfernen.

### 4.2 [MITTEL] Backend-Container
- Läuft als **root** (kein `USER`), `gcc` im Prod-Image, kein Multi-Stage-Build.
- `requirements.txt` installiert `mkdocs*`, `pytest`, `beautifulsoup4`, `sqlalchemy`, `alembic`, `passlib`, `filetype` – im Code ungenutzt (verifiziert via grep). Jedes davon ist Angriffsfläche und pip-audit-Rauschen im Prod-Image.
- Prod-Compose mountet `./backend:/app` ("for development") → Image-Inhalt ist irrelevant, es läuft was auf dem Host liegt; `.env` wird doppelt bereitgestellt (`env_file` + Volume).
- `.gitignore` enthält `.dockerignore` → es kann kein `.dockerignore` committet werden; `COPY . .` kopiert `venv/`, `.env`, `tests/`, `__pycache__` ins Image, falls lokal vorhanden.
- Floating Tags (`python:3.13-slim`, `node:20-alpine`, `nginx:alpine`, `traefik:v3`) ohne Digest.

### 4.3 [MITTEL] HTTP-Header / TLS
- **Kein HSTS** – weder Traefik, nginx noch Backend setzen `Strict-Transport-Security`.
- Frontend ohne CSP; nginx setzt nur `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`.
- nginx-Falle: der `location ~* \.(js|css|...)`-Block hat ein eigenes `add_header` → die Header aus dem `server`-Block werden dort **nicht** vererbt; alle statischen Assets kommen ohne Security-Header.
- `server_tokens off` fehlt.
- Empfehlung: eine Traefik-`headers`-Middleware für beide Router (HSTS mit `includeSubDomains`, CSP, `Referrer-Policy`, `Permissions-Policy`, `X-Content-Type-Options`), dann muss nginx nichts mehr setzen.

### 4.4 [NIEDRIG] Traefik
- `--log.level` Default `DEBUG` in Prod → sehr gesprächige Logs (Header, Routing).
- Docker-Socket gemountet (ro) – üblich, aber ein `docker-socket-proxy` mit nur `GET /containers` ist der bessere Standard.
- Sowohl `httpchallenge` als auch `tlschallenge` konfiguriert; eins genügt.
- `./letsencrypt/acme.json` enthält private Schlüssel und ist **nicht** in `.gitignore`.

---

## 5. Abhängigkeiten (Stand 2026-09-05)

### Python (`pip-audit` auf frischer Installation von `requirements.txt`)

| Paket | installiert | Advisory | Fix |
|---|---|---|---|
| aiosmtplib | 3.0.1 (gepinnt) | PYSEC-2026-2338, CVE-2026-55558 | 5.1.2 (Major-Bump, API prüfen) |
| orjson | 3.11.5 (gepinnt) | PYSEC-2026-107 | 3.11.6 |
| python-dotenv | 1.0.0 (gepinnt, ungenutzt) | PYSEC-2026-2270 | 1.2.2 oder entfernen |
| pytest | 7.4.4 (gepinnt) | PYSEC-2026-1845 | 9.0.3 |

`bandit`: nur die bereits in `SECURITY.md` dokumentierten B104/B110-Befunde, plus B110 in `utils/auth.py:35` (`except Exception: pass` schluckt auch Konfigurationsfehler bei der JWT-Prüfung – mindestens `logger.debug(exc_info=True)`).

### npm (`npm audit`, 5× HIGH, 0 critical)

| Paket | direkt? | Themen | Fix |
|---|---|---|---|
| vite 6.4.1 | ja | Path Traversal in `.map`, Arbitrary File Read via Dev-Server-WebSocket (nur Dev-Server betroffen) | `npm audit fix` |
| lodash | transitiv | Code Injection `_.template`, Prototype Pollution | `npm audit fix` |
| postcss | transitiv | XSS via `</style>`, Arbitrary File Read via sourceMappingURL | `npm audit fix` |
| picomatch | transitiv | ReDoS | `npm audit fix` |
| nanoid | transitiv | Endlosschleife | `npm audit fix` |

Alle npm-Befunde betreffen Build-/Dev-Tooling, nicht das ausgelieferte Bundle. Trotzdem: `npm audit fix` läuft ohne `--force` durch.

### Strukturell
- Python: kein Lockfile, `>=`-Ranges → jeder Build zieht andere Versionen. Auf `uv lock`/`pip-compile --generate-hashes` umstellen; Prod-/Dev-/Docs-Abhängigkeiten trennen (`requirements.txt`, `requirements-dev.txt`, `docs-requirements.txt` gibt es ja schon).
- `SECURITY.md` referenziert `CVE-2026-24486` für python-multipart; die Kommentare in `requirements.txt` sind nur so lange richtig, wie niemand prüft – genau das soll die Pipeline übernehmen.

---

## 6. CI/CD und Repository-Prozesse

**Befund: Es gibt keine Pipeline.**

- Kein `.github/`-Verzeichnis, keine Workflows (GitHub-API listet nur den automatischen `pages-build-deployment`).
- Kein `dependabot.yml`; GitHub-API zeigt **null** Dependabot-PRs seit Repo-Erstellung. Ob Dependabot-Alerts/Secret Scanning in den Repo-Settings aktiv sind, ist per API in dieser Session nicht prüfbar – bitte unter *Settings → Code security* nachsehen.
- Alle 17 PRs stammen vom selben Autor und wurden 1–25 Minuten nach Erstellung gemerged. Kein Review, keine Required Checks, offensichtlich kein Branch-Protection-Regelwerk auf `main`.
- Tests (`pytest`, 8 Tests, grün) und `npm run build` werden nirgends automatisch ausgeführt. `pip-audit`/`npm audit`/`bandit` laufen nur, wenn jemand daran denkt (letzter dokumentierter Lauf: 2026-03-05, seitdem 4 neue Python-Advisories).
- Deployment ist manuell (`docker compose up -d --build` auf dem Server, laut `README.docker.md`); kein Image-Build in CI, kein Image-Scan, keine SBOM, keine Tags/Releases (CLAUDE.md spricht von v2.0.0/v2.1.0, `git tag` ist leer).
- `docs/` ist getrackt und wird per GitHub Pages veröffentlicht, steht aber gleichzeitig in `.gitignore`. Änderungen an `mkdocs/` landen nur auf Pages, wenn jemand lokal `mkdocs build` ausführt und das Ergebnis committet.

### Empfohlene Minimal-Pipeline

1. **`.github/dependabot.yml`** – Ökosysteme `pip` (`/backend`), `npm` (`/frontend`), `docker` (`/backend`, `/frontend`), `github-actions` (`/`); wöchentlich; Gruppierung von Minor/Patch, damit es nicht 30 PRs pro Woche werden.
2. **`ci.yml`** (auf `pull_request` und `push` nach `main`):
   - Backend: `pip install -r requirements.txt`, `pytest`, `bandit -r app -ll`, `pip-audit -r requirements.txt --strict`.
   - Frontend: `npm ci`, `npm audit --audit-level=high`, `npx tsc --noEmit` (TypeScript als devDependency ergänzen), `npm run build`.
   - Docker: `docker build` beider Images, `trivy image --severity HIGH,CRITICAL --exit-code 1`.
   - Secret-Scan: `gitleaks` (Repo-History ist aktuell sauber, verifiziert; das soll so bleiben).
3. **Branch Protection auf `main`:** Required Status Checks (die Jobs aus 2), mindestens ein Review (auch wenn man sich selbst nicht reviewen kann – dann Required Checks als Minimum), keine Force-Pushes.
4. **Docs:** `mkdocs build --strict` in CI und Pages-Deploy per Workflow aus `mkdocs/` statt getrackter `docs/`.
5. **Release/Deploy:** Images in CI bauen, mit Git-SHA taggen, auf dem Server nur noch `pull` statt `build`. Das macht den Quellcode-Mount in `docker-compose.yml` überflüssig.
6. Optional: `CODEOWNERS`, PR-Template, Conventional-Commit-Lint.

---

## 7. Dokumentation

- `CLAUDE.md` ("File uploads: always sanitize filenames and validate magic bytes") und `mkdocs/security.md` (Abschnitt "Magic-Bytes-Validierung", OWASP-Tabelle A08 "Behoben") beschreiben eine Prüfung, die in `dd4b6da` entfernt wurde. `SECURITY.md` dokumentiert die Entfernung korrekt. Drei Quellen, zwei Aussagen.
- `SECURITY.md` "Status: Alle gefundenen Schwachstellen behoben" – siehe oben.
- `.env.example` (Root, veraltetes Backend-Format) und `env.example` (aktuelles Format) existieren parallel; `.env.example` löschen.
- `README.docker.md` beschreibt `LOG_REDACTION_SECRET=change-me` als Beispiel für Prod.

---

## 8. Priorisierte Maßnahmen

**Sofort (wenige Zeilen, kein Risiko):**
1. `--proxy-headers --forwarded-allow-ips=<traefik>` im Uvicorn-CMD (2.1).
2. `GET /api/upload/status/{project_id}` entfernen (2.2).
3. Fehlerdetails aus HTTP-Responses entfernen (2.5).
4. `ports: 3000:80` beim Frontend entfernen (4.1); `letsencrypt/` in `.gitignore` (4.4).
5. `aiosmtplib`, `orjson` aktualisieren; `npm audit fix` (5).
6. Docs konsistent machen (7).

**Kurzfristig:**
7. Body-Limit in Traefik + Dateianzahl-Limit + Streaming in Temp-Datei (2.3).
8. Längen-/Allowlist-Validierung aller Formularfelder, `file_categories` typisieren (2.6).
9. Zufallsanteil in `project_id`, Kollisionsprüfung (2.4).
10. Sync-WebDAV in Threads auslagern (2.8).
11. HSTS/CSP per Traefik-Middleware, nginx aufräumen (4.3).
12. Dependabot + CI-Workflow + Branch Protection (6).

**Mittelfristig:**
13. Dockerfile: Multi-Stage, non-root, ungenutzte Pakete raus, `.dockerignore` erlauben, Digest-Pinning (4.2).
14. Entscheidung zu Bot-Schutz/Double-Opt-in für den E-Mail-Versand (2.7) und ehrliche Neubewertung des Token-Flows in der Doku (2.9).
15. Python-Lockfile mit Hashes, Trennung Prod/Dev/Docs-Requirements (5).
