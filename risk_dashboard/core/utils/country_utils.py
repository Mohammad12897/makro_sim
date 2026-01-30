# core/utils/country_utils.py
import json
from pathlib import Path
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parents[1]
COUNTRY_FILE = BASE_DIR / "data" / "countries.json"


def load_countries() -> List[Dict]:
    with open(COUNTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_countries() -> List[str]:
    data = load_countries()
    return [c["name"] for c in data]


def normalize_country_name(name: str) -> str:
    return name.strip().lower()


def country_to_region(name: str) -> str:
    # einfache Zuordnung über countries.json (dort: name, region)
    data = load_countries()
    key = normalize_country_name(name)
    for c in data:
        if normalize_country_name(c["name"]) == key or key in [normalize_country_name(a) for a in c.get("aliases", [])]:
            return c.get("region", "Global")
    return "Global"
