# Systemarchitektur des Makro Risk Dashboards

Dieses Dokument beschreibt die modulare Architektur des Projekts *makro_sim / risk_dashboard*.

---

## 1. Überblick

Das Dashboard besteht aus drei Hauptkomponenten:

1. **Makro-Modul**  
   Lädt und visualisiert makroäkonomische Zeitreihen.

2. **Risk Engine**  
   Berechnet einen aggregierten Risikoscore aus mehreren Makro-Faktoren.

3. **FX-Modul**  
   Trainiert ein Modell zur Vorhersage des USD/EUR-Wechselkurses.

Alle Module sind vollständig getrennt und kommunizieren nur Ã¼ber definierte Schnittstellen.

---

## 2. Ordnerstruktur
risk_dashboard/
├──	data/						#	CSV-Dateien
├──	models/						#	ML-Modelle
├──	src/
│	├──	app.py					#	Streamlit UI
│	├──	core/					#	Kernlogik
│	│	├──	risk_engine.py
│	│	├──	fx_model.py
│	│	├──	macro_loader.py
│	│	└──	utils.py
│	├──	features/				#	Feature Engineering
│	│	└──	fx_features.py
│	├──	training/				#	Trainingsskripte
│	│	└──	train_fx_model.py
│	└──	visualization/			#	Charts
│		├──	macro_charts.py
│		├──	risk_charts.py
│		└──	fx_charts.py
├──	config/
│	└── settings.yaml
└──	docs/
	├──	lexikon.md
	├──	architecture.md
	└──	onboarding.md



## 3. Datenfluss

1. Datenquelle
   - Rohdaten liegen als CSV in risk_dashboard/data/.
   - Externe APIs (FRED, BLS, Börsen) werden über src/core/macro_loader.py angebunden.

2. Ingestion
   - CSVs und API‑Daten werden in ein standardisiertes Format transformiert und in data/processed/ abgelegt.

3. Feature Engineering
   - src/features/fx_features.py erzeugt FX‑ und Makrofeatures.
   - Missing Values werden imputiert; Zeitreihen werden resampled und synchronisiert.

4. Modelltraining
   - Trainingsskripte in src/training/ nutzen die verarbeiteten Features.
   - Modelle werden in models/ persistiert.

5. Risiko‑Engine
   - src/core/risk_engine.py lädt Modelle, berechnet Risk Scores und erzeugt Alerts.

6. Visualisierung und UI
   - src/visualization/* erzeugt Diagramme.
   - src/app.py (Streamlit) stellt Dashboards und Reports bereit.

7. Konfiguration und Deployment
   - Einstellungen in config/settings.yaml.
   - Dokumentation in docs/ für Onboarding und Architektur.


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

Eine robuste, modulare, reproduzierbare Plattform für makroäkonomische Risikoanalyse.
