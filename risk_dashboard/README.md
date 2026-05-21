# Makro Risk Dashboard â€“ Professional Edition

Dieses Projekt ist ein interaktives Dashboard zur Analyse von:

- makroökonomischen Risiken  
- geopolitischen Abhängigkeiten  
- Energie-, Währungs- und Finanzrisiken  
- politischer & sicherheitspolitischer Abhängigkeit  
- strategischer Autonomie  
- Szenarien, Clustern, Heatmaps und Storylines  

## Struktur

- `core/`
  - `risk_model.py` ‑ Berechnung aller Risiko-Dimensionen
  - `scenario_engine.py` ‑ Schock- und Szenario-Engine
  - `cluster.py` ‑ Clusteranalyse
  - `heatmap.py` ‑ Heatmap-Tabellen
  - `storyline.py` ‑ narrative Risiko-Storyline
  - `ews.py` ‑ Early-Warning-System
- `ui/`
  - `app.py` ‑ Gradio-App mit allen Tabs
  - `components.py` ‑ Radarplots, Dropdowns, UI-Komponenten
  - `layout.py` ‑ Layout-Bausteine (optional genutzt)
- `data/`
  - `slider_presets.json` ‑ Länder-Presets (10 Länder inkl. Israel)
  - `scenario_presets.json` ‑ Szenario-Definitionen

## Start

1. Stelle sicher, dass der Projekt-ROOT korrekt ist:

   ```python
   ROOT = "/content/makro_sim/risk_dashboard"

