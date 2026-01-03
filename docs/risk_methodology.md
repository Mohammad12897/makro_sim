# Risiko-Modell – Methodikdokumentation

## 1. Ziel des Modells
Das Modell bewertet makroökonomische, geopolitische und Governance-Risiken von Ländern anhand eines einheitlichen, transparenten Scoring-Systems.

## 2. Datenbasis
- Länder-Presets (manuell gepflegt)
- Optional: World-Bank-Indikatoren
- 17 UI-Slider-Parameter

## 3. Normalisierung
### 3.1 Makro
- Verschuldung: exponentielle Normalisierung
- FX-Schockempfindlichkeit: lineare Skalierung
- Reserven: logarithmische Normalisierung

### 3.2 Geo
- USD-Dominanz: linear
- Sanktions-Exposure: verstärkte Gewichtung
- Alternativnetz: invertiert, exponentiell

### 3.3 Governance
- Demokratie: invertiert
- Korruption: stark gewichtet
- Innovation: linear
- Fachkräfte: linear

## 4. Risiko-Formel Version 2
- total = 0.40 * macro + 0.35 * geo + 0.25 * governance

## 5. Kategorien
| Score | Kategorie |
|--------|-----------|
| <0.33 | stabil |
| 0.33–0.66 | warnung |
| >0.66 | kritisch |

## 6. Sensitivitätsanalyse
- Δ Risiko <0.02 → gering
- Δ Risiko 0.02–0.05 → mittel
- Δ Risiko 0.05–0.10 → hoch
- Δ Risiko >0.10 → sehr hoch

## 7. Szenario-Schocks
- <10% → gering
- 10–20% → mittel
- 20–35% → hoch
- >35% → sehr hoch

## 8. Heatmap
Visualisiert Makro-, Geo-, Governance- und Total-Risiken farbcodiert.

## 9. Grenzen des Modells
- Keine Echtzeitdaten
- Keine politischen Ereignisse
- Keine Marktpreise
