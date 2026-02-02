# core/data/country_macro.py

import json
import os

# Absoluter Pfad zu slider_presets.json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# → geht von core/data → core → risk_dashboard
PRESETS_PATH = os.path.join(BASE_DIR, "data", "slider_presets.json")


# Datei laden
with open(PRESETS_PATH, "r", encoding="utf-8") as f:
    PRESETS = json.load(f)

# Länder-Makrodaten extrahieren
COUNTRY_MACRO = PRESETS.get("countries", {})

def get_country_macro(country: str) -> dict:
    return COUNTRY_MACRO.get(country, {
        "BIP-Wachstum": 0,
        "Inflation": 0,
        "Zinsen": 0,
        "Arbeitslosenquote": 0,
    })
