# Systemarchitektur des Makro Risk Dashboards

Dieses Dokument beschreibt die modulare Architektur des Projekts *makro_sim / risk_dashboard*.

---

## 1. Überblick

Das Dashboard besteht aus drei Hauptkomponenten:

1. **Makro-Modul**  
   Lädt und visualisiert makroökonomische Zeitreihen.

2. **Risk Engine**  
   Berechnet einen aggregierten Risikoscore aus mehreren Makro-Faktoren.

3. **FX-Modul**  
   Trainiert ein Modell zur Vorhersage des USD/EUR-Wechselkurses.

Alle Module sind vollständig getrennt und kommunizieren nur über definierte Schnittstellen.

---

## 2. Ordnerstruktur
risk_dashboard/ │ ├── data/                 # CSV-Dateien ├── models/               # ML-Modelle │ ├── src/ │   ├── app.py            # Streamlit UI │   │ │   ├── core/             # Kernlogik │   │   ├── risk_engine.py │   │   ├── fx_model.py │   │   ├── macro_loader.py │   │   └── utils.py │   │ │   ├── features/         # Feature Engineering │   │   └── fx_features.py │   │ │   ├── training/         # Trainingsskripte │   │   └── train_fx_model.py │   │ │   ├── visualization/    # Charts │   │   ├── macro_charts.py │   │   ├── risk_charts.py │   │   └── fx_charts.py │   │ │   └── config/ │       └── settings.yaml │ └── docs/ ├── lexikon.md ├── architecture.md └── onboarding.md

---

## 3. Datenfluss

### Makro-Daten
CSV → macro_loader → app.py → Charts + Risk Engine

### Risk Engine
macro_data → risk_engine → risk_snapshot → app.py

### FX-Modell
fx_data → fx_features → train_fx_model → rf_model.joblib → fx_model → app.py

---

## 4. Erweiterbarkeit

Die Architektur erlaubt:

- neue Risiko-Faktoren
- neue ML-Modelle
- neue Visualisierungen
- neue Datenquellen
- Szenario-Simulationen
- API-Anbindung

---

## 5. Ziel

Eine robuste, modulare, reproduzierbare Plattform für makroökonomische Risikoanalyse.