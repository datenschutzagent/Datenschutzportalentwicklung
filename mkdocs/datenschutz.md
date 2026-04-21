# Datenschutz und Verarbeitungstätigkeiten

Diese Dokumentation beschreibt die Verarbeitung personenbezogener Daten und projektbezogener Informationen innerhalb des Datenschutzportals.

## Überblick der Verarbeitung

Das Portal dient der digitalen Einreichung von Datenschutzunterlagen für Forschungsprojekte. Die Daten werden vom Nutzer eingegeben, validiert, sicher übertragen und in einer internen Nextcloud-Instanz gespeichert.

### Datenkategorien

Im Rahmen der Nutzung werden folgende Datenkategorien verarbeitet:

1.  **Personenbezogene Daten des Einreichers:**
    *   Name (Optional)
    *   E-Mail-Adresse (Pflichtfeld zur Kontaktaufnahme und Bestätigung)
    *   Zugehörige Institution (Universität Frankfurt oder Universitätsklinikum)

2.  **Projektdaten:**
    *   Projekttitel
    *   Projektbeschreibung / Details
    *   Art der Studie (z.B. prospektiv)
    *   Projekttyp (Neueinreichung oder Nachreichung zu bestehendem Projekt)

3.  **Dokumente:**
    *   Datenschutzkonzepte
    *   Verantwortungsübernahmen
    *   Schulungsnachweise
    *   Einwilligungserklärungen
    *   Ethikvoten
    *   Sonstige projektbezogene Dateien

## Technische Verarbeitung

### 1. Upload und Validierung

*   Daten werden über eine verschlüsselte Verbindung (HTTPS via Traefik/Let's Encrypt) an die API übermittelt.
*   Die API validiert Dateitypen anhand von Dateiendungen (Allowlist) **und** Dateiinhalt (Magic-Bytes-Prüfung via `filetype`-Bibliothek).
*   Dateigrößen werden gegen ein konfigurierbares Limit geprüft (Standard: 50 MB).
*   Dateinamen werden sanitiert (Entfernung von Pfadkomponenten, Sonderzeichen), um Path-Traversal-Angriffe zu verhindern.
*   Projekttitel werden für die Ordnerstruktur bereinigt.

### 2. Speicherung (Nextcloud)

*   Die Speicherung erfolgt in einer intern gehosteten Nextcloud-Instanz.
*   Für jedes Projekt wird ein eindeutiger Ordner basierend auf dem Projekttitel und dem Datum erstellt.
*   Dateien werden in Unterordnern gemäß ihrer Kategorie (z.B. „datenschutzkonzept") abgelegt.
*   Zusätzlich wird eine `metadata.json` (maschinenlesbar) und eine `README.md` (menschenlesbar) mit allen Projektinformationen generiert und gespeichert.

### 3. Benachrichtigungen (E-Mail)

Das System versendet automatisch E-Mails über einen konfigurierten SMTP-Server:

*   **Bestätigung an den Nutzer:** Enthält eine Zusammenfassung der eingereichten Dateien und die Projekt-ID.
*   **Benachrichtigung an das Team:** Informiert die Datenschutzbeauftragten über den neuen Eingang.

Alle nutzerkontrollierten Werte werden vor der Einbettung in HTML-E-Mails mit `html.escape()` escapt (XSS-Schutz).

## Zugriff und Sicherheit

*   **Authentifizierung:** Die API verwendet einen zweistufigen Token-Exchange-Flow. Der statische API-Token wird gegen einen kurz-lebigen JWT (5 Minuten Gültigkeit) getauscht, der für den eigentlichen Upload-Vorgang verwendet wird. Details: [Sicherheitsdokumentation](security.md).
*   **Rate Limiting:** Upload-Endpunkte sind auf 10 Anfragen/Stunde pro IP begrenzt.
*   **Zugriff:** Zugriff auf die gespeicherten Daten in der Nextcloud haben nur autorisierte Mitarbeiter des Datenschutzteams.
*   **Verschlüsselung:** Die Übertragung erfolgt transportverschlüsselt (TLS). Die Speicherung auf dem Server unterliegt den Sicherheitsstandards des Rechenzentrums.
*   **Logging:** E-Mail-Adressen und andere PII werden in Logs ausschließlich als HMAC-Hash gespeichert (kein Klartext-Logging von personenbezogenen Daten).

## Löschfristen

Die Daten werden gemäß den gesetzlichen Aufbewahrungsfristen für Forschungsvorhaben und Datenschutzdokumentation gespeichert. Nach Ablauf der Zweckbindung oder der gesetzlichen Fristen werden die Daten gelöscht.
