#!/usr/bin/env python3
# coding: utf-8
"""
Konvertiert country_presets.json (Indicator-Snapshots) in slider_presets.json (UI-Presets).

Aktuell: Skeleton mit Dummy-Mapping.
Später: Logik einbauen, um Indikatoren auf Slider (0..1 o.ä.) zu mappen.
"""

from __future__ import annotations
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRESETS_DIR = BASE_DIR / "presets"
COUNTRY_FILE = PRESETS_DIR / "country_presets.json"
SLIDER_FILE = PRESETS_DIR / "slider_presets.json"


def load_json(path: Path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def country_to_slider_preset(country_code: str, country_preset: dict) -> dict:
    """
    Dummy-Konvertierung: Hier definierst du später,
    wie aus Indicator-Snapshots konkrete Sliderwerte werden.

    Aktuell: nur ein Beispiel mit Defaults.
    """
    # Beispiel-Struktur – hier musst du deine PARAM_SLIDERS kennen
    slider_preset = {
        "energie": 0.5,
        "innovation": 0.5,
        "verschuldung": 0.5,
        "stabilitaet": 0.5,
        # ...
    }

    snapshot = country_preset.get("indicator_snapshot", {}) or {}

    # Beispiele (Platzhalter-Logik):
    # Du kannst hier aus snapshot[...] Werte normalisieren.

    # z.B. Verschuldung basierend auf DT_DOD_DECT_CD / NY_GDP_MKTP_CD
    try:
        debt = snapshot.get("DT_DOD_DECT_CD", {}).get("value")
        gdp = snapshot.get("NY_GDP_MKTP_CD", {}).get("value")
        if debt is not None and gdp:
            ratio = debt / gdp
            # einfache Normalisierung, z.B. 0..1 bei 0..3
            slider_preset["verschuldung"] = max(0.0, min(1.0, ratio / 3.0))
    except Exception:
        pass

    # Weitere Mappings kannst du später definieren...

    return slider_preset


def main():
    countries = load_json(COUNTRY_FILE)
    slider_presets = load_json(SLIDER_FILE)

    if not isinstance(countries, dict):
        print("country_presets.json ist nicht vom Typ dict – Abbruch.")
        return

    for code, country_preset in countries.items():
        try:
            slider_presets[code] = country_to_slider_preset(code, country_preset)
            print(f"Generated slider preset for {code}")
        except Exception as e:
            print(f"Error generating slider preset for {code}: {e}")

    SLIDER_FILE.write_text(json.dumps(slider_presets, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {SLIDER_FILE} with {len(slider_presets)} slider presets")


if __name__ == "__main__":
    main()
