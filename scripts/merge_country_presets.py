#!/usr/bin/env python3
# coding: utf-8
"""
Merge presets/preset_*.json into presets/country_presets.json

- Jede Datei preset_*.json enthält ein Länder-Preset mit Indicator-Snapshot + Metadaten.
- Der Output ist ein Dict: { "BR": {...}, "DE": {...}, ... } in country_presets.json.

NEU:
- Fehlende Keys (z.B. 'korruption') werden automatisch ergänzt.
- Alle Werte werden auf gültige Bereiche gemäß PARAM_SLIDERS geclamped.
"""

from __future__ import annotations
import json
import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

PRESETS_DIR = Path("presets")
OUT_FILE = PRESETS_DIR / "country_presets.json"

# --- NEU: Default-Werte für fehlende Keys ---
DEFAULTS = {
    "USD_Dominanz": 0.7,
    "RMB_Akzeptanz": 0.2,
    "Zugangsresilienz": 0.8,
    "Sanktions_Exposure": 0.05,
    "Alternativnetz_Abdeckung": 0.5,
    "Liquiditaetsaufschlag": 0.03,
    "CBDC_Nutzung": 0.5,
    "Golddeckung": 0.4,
    "innovation": 0.6,
    "fachkraefte": 0.7,
    "energie": 0.5,
    "stabilitaet": 0.9,
    "verschuldung": 0.8,
    "demokratie": 0.8,
    "FX_Schockempfindlichkeit": 0.8,
    "Reserven_Monate": 6,
    "korruption": 0.3,   # NEU
}

# --- NEU: Gültige Bereiche (Clamping) ---
RANGES = {
    "USD_Dominanz": (0, 1),
    "RMB_Akzeptanz": (0, 1),
    "Zugangsresilienz": (0, 1),
    "Sanktions_Exposure": (0, 1),
    "Alternativnetz_Abdeckung": (0, 1),
    "Liquiditaetsaufschlag": (0, 1),
    "CBDC_Nutzung": (0, 1),
    "Golddeckung": (0, 1),
    "innovation": (0, 1),
    "fachkraefte": (0, 1),
    "energie": (0, 1),
    "stabilitaet": (0, 1),
    "verschuldung": (0, 2),
    "demokratie": (0, 1),
    "FX_Schockempfindlichkeit": (0, 2),
    "Reserven_Monate": (0, 24),
    "korruption": (0, 1),
}

def clamp(value, lo, hi):
    try:
        v = float(value)
    except:
        return lo
    return max(lo, min(hi, v))

def sanitize_preset(preset: dict) -> dict:
    """Ergänzt fehlende Keys und clamp’t Werte in gültige Bereiche."""
    clean = {}

    for key, default in DEFAULTS.items():
        val = preset.get(key, default)
        lo, hi = RANGES[key]
        clean[key] = clamp(val, lo, hi)

    return clean

def main(strategy="overwrite"):
    PRESETS_DIR.mkdir(exist_ok=True)

    merged = {}

    for file in PRESETS_DIR.glob("preset_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Fehler beim Lesen von {file}: {e}")
            continue

        # Länder-Code aus Dateiname extrahieren
        code = file.stem.replace("preset_", "").upper()

        # Sanitize
        clean = sanitize_preset(data)

        if strategy == "skip" and code in merged:
            continue
        elif strategy == "rename" and code in merged:
            i = 2
            new_code = f"{code}_{i}"
            while new_code in merged:
                i += 1
                new_code = f"{code}_{i}"
            code = new_code

        merged[code] = clean

    # Schreiben
    OUT_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"country_presets.json aktualisiert ({len(merged)} Länder).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["overwrite", "skip", "rename"], default="overwrite")
    args = parser.parse_args()
    main(args.strategy)
