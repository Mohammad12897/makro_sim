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


# makro_sim – ETF Analyse & Portfolio Backtesting Dashboard

Ein interaktives Streamlit‑Dashboard zur Analyse, Bewertung und Simulation von ETF‑Portfolios.  
Das System kombiniert ETF‑Scoring, Portfolio‑Optimierung, Backtesting und Visualisierung in einer klaren, intuitiven Oberfläche.

---

## 🚀 Features

- **ETF‑Scoring** nach TER, AUM, Tracking, Replikation, Liquidität  
- **Explainable Breakdown** für transparente Bewertung  
- **Portfolio‑Optimierung** (HRP, Equal Weight, Minimum Variance)  
- **Manuelle oder automatische Gewichtung**  
- **Backtesting** mit Rebalancing  
- **Kumulative Performance‑Charts**  
- **Gewichtsentwicklung über Zeit**  
- **Export von CSV & JSON**  
- **Stabile Session‑State‑Architektur (keine Reload‑Probleme)**  

---

## 📦 Installation

```bash
git clone https://github.com/<dein-repo>/makro_sim.git
cd makro_sim
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

