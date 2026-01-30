# core/utils/country_utils.py
import json
from pathlib import Path

COUNTRY_FILE = Path(__file__).resolve().parents[1] / "data" / "countries.json"

def load_countries():
    with open(COUNTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_all_countries():
    return [c["name"] for c in load_countries()]

def country_to_region(name):
    name = name.lower().strip()
    for c in load_countries():
        if name == c["name"].lower() or name in [a.lower() for a in c.get("aliases", [])]:
            return c["region"]
    return "Global"
