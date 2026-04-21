# Allgemeine Richtlinien

Dieses Dokument beschreibt die allgemeinen Coding- und Projekt-Richtlinien für das Datenschutzportal.

## Sprachen

| Bereich | Sprache |
|---------|---------|
| Quellcode (Variablen, Funktionen, Kommentare) | Englisch |
| Externe Dokumentation (MkDocs, diese Datei) | Deutsch |
| E-Mail-Templates, UI-Texte | Deutsch und Englisch (i18n) |
| Git-Commit-Messages | Englisch (Conventional Commits) |

Kommentare im Code erklären das **Warum**, nicht das Was. Offensichtlichen Code nicht kommentieren.

## Architektur-Grundsätze

- **Modularität**: Code in kleine, fokussierte Funktionen und Module aufteilen. Eine Funktion, eine Aufgabe.
- **Keine vorzeitigen Abstraktionen**: Abstrahiere erst, wenn ein Muster dreimal auftritt – nicht vorher.
- **Bibliotheken bevorzugen**: Vorhandene, gepflegte Bibliotheken nutzen statt Eigenimplementierungen.
- **Kein toter Code**: Ungenutzte Variablen, Funktionen und Importe entfernen.
- **Keine Kompatibilitäts-Shims**: Keine Rückwärtskompatibilitäts-Hacks für entfernte Features.

## Datei-Organisation

- **Kleine Dateien**: Hilfsfunktionen und Komponenten in eigene Dateien auslagern.
- **Frontend**: Jede Komponente in eigener Datei unter `src/components/`; UI-Primitives unter `src/components/ui/`.
- **Backend**: Routes, Services und Models strikt trennen (`app/routes/`, `app/services/`, `app/models/`).
- **Keine Barrel-Exports** ohne klaren Mehrwert.

## Layout & CSS (Frontend)

- **Flexbox und Grid bevorzugen**: `position: absolute` nur wenn zwingend nötig.
- **Tailwind-Klassen-Reihenfolge**: Layout → Abstand → Typografie → Farben → Effekte.
- **Responsive by default**: Mobile-first entwerfen.
- **Keine Duplikation**: Wiederkehrende Klassen-Kombinationen als Komponente extrahieren.

Beispiel für korrekte Reihenfolge:
```tsx
<div className="flex flex-col gap-4 p-6 text-lg bg-white text-gray-900 rounded-lg shadow-md">
```

## Sicherheit

- **Keine Secrets im Code**: API-Keys, Passwörter und Tokens ausschließlich über Umgebungsvariablen.
- **Eingaben validieren**: Alle externen Eingaben (Formulare, API-Parameter) server-seitig validieren.
- **Keine `any`-Typen** in TypeScript: `unknown` verwenden und explizit casten.
- **HTML-Ausgabe escapen**: Nutzereingaben, die in HTML eingebettet werden, mit `html.escape()` (Python) oder dem React-Escaping behandeln.

## Emoji-Policy

Keine Emojis in Code, Kommentaren, Dokumentation oder Commit-Messages – es sei denn, der Nutzer bittet ausdrücklich darum.

## Version Control

- **Regelmäßige Commits**: Kleine, atomare Commits mit klaren Nachrichten.
- **Conventional Commits**: Format `<type>(<scope>): <subject>` (Details in [Contributing](contributing.md)).
- **Branch-Namen**: `feature/`, `fix/`, `docs/`, `refactor/`, `test/` als Präfixe.
- **Kein Force-Push auf `main`**.

## Code-Qualität

- **Refaktoriere laufend**: Technische Schulden direkt beim Bearbeiten der Datei beheben, nicht ansammeln.
- **Early Return bevorzugen**: Tief verschachtelte `if`-Blöcke vermeiden.
- **TypeScript Strict Mode**: Immer eingeschaltet; keine Unterdrückung von Typ-Fehlern mit `// @ts-ignore`.
- **Python PEP 8**: Einhalten; Type Hints für alle öffentlichen Funktionen.
