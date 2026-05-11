# Onboarding Guide für das Makro Risk Dashboard

Willkommen im Projekt! Dieses Dokument erklärt, wie du das Dashboard installierst, startest und erweiterst.

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

### Abhängigkeiten installieren
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

- `core/` → Business-Logik  
- `features/` → Feature Engineering  
- `training/` → ML-Training  
- `visualization/` → Charts  
- `config/` → Einstellungen  
- `docs/` → Dokumentation  

---

## 7. Häufige Probleme

### Modell nicht gefunden
→ `train_fx_model.py` ausführen.

### Daten fehlen
→ CSVs in `risk_dashboard/data/` prüfen.

### Pfadprobleme
→ `settings.yaml` prüfen.

---

## 8. Erweiterungsideen

- Szenario-Simulationen
- Stress-Tests
- API-Anbindung (FRED, ECB)
- ML-Modelle für Makro-Prognosen
