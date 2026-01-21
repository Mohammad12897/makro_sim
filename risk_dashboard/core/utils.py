# core/utils.py
import json
import os

BASE_PATH = "/content/makro_sim/risk_dashboard/data"


def load_json(filename: str):
    """Hilfsfunktion zum Laden einer JSON-Datei."""
    path = os.path.join(BASE_PATH, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_presets():
    """
    Lädt die Länder-Presets aus slider_presets.json.
    """
    return load_json("slider_presets.json")


def load_scenarios():
    """
    Lädt die Szenarien aus scenarios.json.
    """
    return load_json("scenario_presets.json")
