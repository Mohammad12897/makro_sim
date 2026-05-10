# Systemarchitektur des Makro Risk Dashboards

Dieses Dokument beschreibt die modulare Architektur des Projekts *makro_sim / risk_dashboard*.

---

## 1. Ãœberblick

Das Dashboard besteht aus drei Hauptkomponenten:

1. **Makro-Modul**  
   LÃ¤dt und visualisiert makroÃ¶konomische Zeitreihen.

2. **Risk Engine**  
   Berechnet einen aggregierten Risikoscore aus mehreren Makro-Faktoren.

3. **FX-Modul**  
   Trainiert ein Modell zur Vorhersage des USD/EUR-Wechselkurses.

Alle Module sind vollstÃ¤ndig getrennt und kommunizieren nur Ã¼ber definierte Schnittstellen.

---

## 2. Ordnerstruktur
risk_dashboard/ â”‚ â”œâ”€â”€ data/                 # CSV-Dateien â”œâ”€â”€ models/               # ML-Modelle â”‚ â”œâ”€â”€ src/ â”‚   â”œâ”€â”€ app.py            # Streamlit UI â”‚   â”‚ â”‚   â”œâ”€â”€ core/             # Kernlogik â”‚   â”‚   â”œâ”€â”€ risk_engine.py â”‚   â”‚   â”œâ”€â”€ fx_model.py â”‚   â”‚   â”œâ”€â”€ macro_loader.py â”‚   â”‚   â””â”€â”€ utils.py â”‚   â”‚ â”‚   â”œâ”€â”€ features/         # Feature Engineering â”‚   â”‚   â””â”€â”€ fx_features.py â”‚   â”‚ â”‚   â”œâ”€â”€ training/         # Trainingsskripte â”‚   â”‚   â””â”€â”€ train_fx_model.py â”‚   â”‚ â”‚   â”œâ”€â”€ visualization/    # Charts â”‚   â”‚   â”œâ”€â”€ macro_charts.py â”‚   â”‚   â”œâ”€â”€ risk_charts.py â”‚   â”‚   â””â”€â”€ fx_charts.py â”‚   â”‚ â”‚   â””â”€â”€ config/ â”‚       â””â”€â”€ settings.yaml â”‚ â””â”€â”€ docs/ â”œâ”€â”€ lexikon.md â”œâ”€â”€ architecture.md â””â”€â”€ onboarding.md

---

## 3. Datenfluss

### Makro-Daten
CSV â†’ macro_loader â†’ app.py â†’ Charts + Risk Engine

### Risk Engine
macro_data â†’ risk_engine â†’ risk_snapshot â†’ app.py

### FX-Modell
fx_data â†’ fx_features â†’ train_fx_model â†’ rf_model.joblib â†’ fx_model â†’ app.py

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

Eine robuste, modulare, reproduzierbare Plattform fÃ¼r makroÃ¶konomische Risikoanalyse.
