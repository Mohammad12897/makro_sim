---

### Dokumentation für Szenarien (`docs/scenarios.md` – Inhalt)

```markdown
# Szenario-Dokumentation

Dieses Dokument beschreibt die im Dashboard verwendeten Szenarien und ihre Wirkung.

## Grundprinzip

- Jedes Szenario besteht aus einer Liste von **Schocks**.
- Jeder Schock hat:
  - `type` – Bezeichnung, die in `apply_shock()` verarbeitet wird
  - `intensity` – Stärke des Schocks (0–1, Standard 1.0)

Beispiel:

```json
"Ölpreisschock": [
  { "type": "Ölpreis +50%", "intensity": 1.0 }
]
