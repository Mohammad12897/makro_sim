---

### Dokumentation fÃ¼r Szenarien (`docs/scenarios.md` â€“ Inhalt)

```markdown
# Szenario-Dokumentation

Dieses Dokument beschreibt die im Dashboard verwendeten Szenarien und ihre Wirkung.

## Grundprinzip

- Jedes Szenario besteht aus einer Liste von **Schocks**.
- Jeder Schock hat:
  - `type` â€“ Bezeichnung, die in `apply_shock()` verarbeitet wird
  - `intensity` â€“ StÃ¤rke des Schocks (0â€“1, Standard 1.0)

Beispiel:

```json
"Ã–lpreisschock": [
  { "type": "Ã–lpreis +50%", "intensity": 1.0 }
]

