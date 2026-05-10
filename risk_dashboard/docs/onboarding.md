# Onboarding Guide fÃ¼r das Makro Risk Dashboard

Willkommen im Projekt! Dieses Dokument erklÃ¤rt, wie du das Dashboard installierst, startest und erweiterst.

---

## 1. Voraussetzungen

- Python 3.10+
- pip
- virtualenv (optional)
- Git (optional)

---

## 2. Installation

### Virtuelle Umgebung erstellen
python -m venv venv

### Aktivieren

Windows:
.\venv\Scripts\activate

### AbhÃ¤ngigkeiten installieren
pip install -r requirements.txt

---

## 3. Projekt starten
streamlit run risk_dashboard/src/app.py

---

## 4. FX-Modell trainieren
python -m risk_dashboard.src.training.train_fx_model

---

## 5. Ordnerstruktur verstehen

Siehe `architecture.md`.

---

## 6. Wichtige Module

- `core/` â†’ Business-Logik  
- `features/` â†’ Feature Engineering  
- `training/` â†’ ML-Training  
- `visualization/` â†’ Charts  
- `config/` â†’ Einstellungen  
- `docs/` â†’ Dokumentation  

---

## 7. HÃ¤ufige Probleme

### Modell nicht gefunden
â†’ `train_fx_model.py` ausfÃ¼hren.

### Daten fehlen
â†’ CSVs in `risk_dashboard/data/` prÃ¼fen.

### Pfadprobleme
â†’ `settings.yaml` prÃ¼fen.

---

## 8. Erweiterungsideen

- Szenario-Simulationen
- Stress-Tests
- API-Anbindung (FRED, ECB)
- ML-Modelle fÃ¼r Makro-Prognosen

