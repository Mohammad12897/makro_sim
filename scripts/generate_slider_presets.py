#!/usr/bin/env python3
# coding: utf-8
"""
Konvertiert country_presets.json (Indicator-Snapshots) in slider_presets.json (UI-Presets).

- Aggressive Normalisierung der relevanten Indikatoren
- Vollständige 17 UI-Slider-Parameter (inkl. korruption)
- Risiko-Scores (macro, geo, governance, total)
"""

from __future__ import annotations
import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.risk_model import compute_risk_scores, risk_category

import json
import math
from pathlib import Path
from typing import Dict, Tuple

# ---------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PRESETS_DIR = BASE_DIR / "presets"

COUNTRY_PRESETS_FILENAME = PRESETS_DIR / "country_presets.json"
SLIDER_PRESETS_FILENAME = PRESETS_DIR / "slider_presets.json"

# ---------------------------------------------------------------------
# Slider-Definitionen (müssen exakt zu gradio_app.py passen)
# ---------------------------------------------------------------------

default_params: Dict[str, float] = {
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

PARAM_SLIDERS = [
    ("USD_Dominanz", 0.0, 1.0, default_params["USD_Dominanz"]),
    ("RMB_Akzeptanz", 0.0, 1.0, default_params["RMB_Akzeptanz"]),
    ("Zugangsresilienz", 0.0, 1.0, default_params["Zugangsresilienz"]),
    ("Sanktions_Exposure", 0.0, 1.0, default_params["Sanktions_Exposure"]),
    ("Alternativnetz_Abdeckung", 0.0, 1.0, default_params["Alternativnetz_Abdeckung"]),
    ("Liquiditaetsaufschlag", 0.0, 1.0, default_params["Liquiditaetsaufschlag"]),
    ("CBDC_Nutzung", 0.0, 1.0, default_params["CBDC_Nutzung"]),
    ("Golddeckung", 0.0, 1.0, default_params["Golddeckung"]),
    ("innovation", 0.0, 1.0, default_params["innovation"]),
    ("fachkraefte", 0.0, 1.0, default_params["fachkraefte"]),
    ("energie", 0.0, 1.0, default_params["energie"]),
    ("stabilitaet", 0.0, 1.0, default_params["stabilitaet"]),
    ("verschuldung", 0.0, 2.0, default_params["verschuldung"]),
    ("demokratie", 0.0, 1.0, default_params["demokratie"]),
    ("FX_Schockempfindlichkeit", 0.0, 2.0, default_params["FX_Schockempfindlichkeit"]),
    ("Reserven_Monate", 0, 24, default_params["Reserven_Monate"]),
    ("korruption", 0.0, 1.0, default_params["korruption"]),  # NEU
]

# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_ratio(value, min_val=0.0, max_val=2.0) -> float:
    if value is None:
        return 0.5
    x = max(min_val, min(max_val, float(value)))
    return (x - min_val) / (max_val - min_val)

def normalize_log(value, min_log=9.0, max_log=13.0) -> float:
    if value is None or value <= 0:
        return 0.5
    x = math.log10(float(value))
    x = max(min_log, min(max_log, x))
    return (x - min_log) / (max_log - min_log)

def normalize_inflation(value, low=0.0, high=10.0) -> float:
    if value is None:
        return 0.5
    x = max(low, min(high, float(value)))
    return (x - low) / (high - low)

# ---------------------------------------------------------------------
# Risiko-Scores (identisch zu gradio_app.py)
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# Mapping: country_presets.json → Slider-Preset
# ---------------------------------------------------------------------

def country_to_slider_preset(code: str, country_preset: dict) -> dict:
    # Start mit Defaults
    slider = {k: default for (k, _lo, _hi, default) in PARAM_SLIDERS}

    # 1) Direktes Mapping aus flachen Keys (so wie in deiner neuen country_presets.json)
    #    Falls du später wieder indicator_snapshot nutzt, bleibt das unten als Fallback.
    for key in slider.keys():
        if key in country_preset:
            slider[key] = country_preset[key]

    # 2) OPTIONAL: Fallback auf alte indicator_snapshot-Logik, falls vorhanden
    snap = country_preset.get("indicator_snapshot", {}) or {}

    # Verschuldung
    try:
        debt = snap.get("DT_DOD_DECT_CD", {}).get("value")
        gdp = snap.get("NY_GDP_MKTP_CD", {}).get("value")
        if debt and gdp:
            ratio = float(debt) / float(gdp)
            slider["verschuldung"] = normalize_ratio(ratio, 0.0, 2.0) * 2.0
    except Exception:
        pass

    # Reserven
    try:
        res = snap.get("FI_RES_TOTL_MO", {}).get("value")
        if res is not None:
            slider["Reserven_Monate"] = max(0.0, min(24.0, float(res)))
    except Exception:
        pass

    # Offenheit → Zugangsresilienz
    try:
        exports = snap.get("NE_EXP_GNFS_CD", {}).get("value")
        imports = snap.get("NE_IMP_GNFS_CD", {}).get("value")
        if exports and imports:
            openness = normalize_log(exports + imports, 9.0, 13.0)
            # clamp01 kommt aus risk_model; hier entweder selbst definieren oder importieren
            from core.risk_model import clamp01 as _clamp01
            slider["Zugangsresilienz"] = _clamp01(openness)
    except Exception:
        pass

    # Inflation → FX_Schockempfindlichkeit
    try:
        infl = snap.get("FP_CPI_TOTL_ZG", {}).get("value")
        if infl is not None:
            inf_norm = normalize_inflation(infl, 0.0, 10.0)
            slider["FX_Schockempfindlichkeit"] = 0.5 + 1.0 * inf_norm
    except Exception:
        pass

    # Staatsausgabenquote → stabilitaet
    try:
        spend = snap.get("GC_XPN_TOTL_GD_ZS", {}).get("value")
        if spend is not None:
            spend_norm = normalize_ratio(spend / 100.0, 0.0, 0.6)
            from core.risk_model import clamp01 as _clamp01
            slider["stabilitaet"] = _clamp01(1.0 - 0.7 * spend_norm)
    except Exception:
        pass

    # korruption: wenn weder flacher Wert noch Snapshot: Default 0.3
    slider["korruption"] = slider.get("korruption", 0.3)

    return slider
# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------

def main():
    countries = load_json(COUNTRY_PRESETS_FILENAME)
    if not countries:
        print("country_presets.json ist leer oder fehlt.")
        return

    slider_presets = {}

    print("Generiere Slider-Presets (mit Risiko-Scores)…")
    for code, cp in countries.items():
        sp = country_to_slider_preset(code, cp)
        scores = compute_risk_scores(sp)
        cat, _ = risk_category(scores["total"])
        print(f"{code}: total={scores['total']:.2f} ({cat})")
        slider_presets[code] = sp

    save_json(SLIDER_PRESETS_FILENAME, slider_presets)
    print(f"Schreibe {SLIDER_PRESETS_FILENAME} mit {len(slider_presets)} Slider-Presets.")

if __name__ == "__main__":
    main()
