#!/usr/bin/env python3
# coding: utf-8
"""
Konvertiert country_presets.json (Indicator-Snapshots) in slider_presets.json (UI-Presets).

- Aggressive Normalisierung der relevanten Indikatoren
- Vollständige 17 UI-Slider-Parameter (inkl. korruption)
- Risiko-Scores (macro, geo, governance, total)
"""

from __future__ import annotations

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

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

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

def compute_risk_scores(p: dict) -> Dict[str, float]:
    macro = (
        clamp01(p.get("verschuldung", 0.8) / 1.5) * 0.45 +
        clamp01(p.get("FX_Schockempfindlichkeit", 0.8) / 1.5) * 0.35 +
        (1 - clamp01(p.get("Reserven_Monate", 6) / 18.0)) * 0.20
    )

    geo = (
        clamp01(p.get("USD_Dominanz", 0.7)) * 0.45 +
        clamp01(p.get("Sanktions_Exposure", 0.05)) * 0.35 +
        (1 - clamp01(p.get("Alternativnetz_Abdeckung", 0.5))) * 0.20
    )

    korruption = p.get("korruption", 0.3)

    gov = (
        (1 - clamp01(p.get("demokratie", 0.8))) * 0.5 +
        (1 - clamp01(p.get("innovation", 0.6))) * 0.3 +
        (1 - clamp01(p.get("fachkraefte", 0.7))) * 0.2 +
        korruption * 0.15
    )

    total = 0.5 * macro + 0.3 * geo + 0.2 * gov

    finanz = (
        p.get("verschuldung", 0.8) / 2.0 +
        p.get("FX_Schockempfindlichkeit", 0.8) / 2.0
    )

    sozial = (
        (1 - p.get("fachkraefte", 0.7)) * 0.5 +
        (1 - p.get("demokratie", 0.8)) * 0.5
    )

    return {
        "macro": clamp01(macro),
        "geo": clamp01(geo),
        "governance": clamp01(gov),
        "finanz": clamp01(finanz),
        "sozial": clamp01(sozial),
        "total": clamp01(total),
    }
    
def risk_category(score: float):
    if score < 0.33:
        return "stabil", "green"
    elif score < 0.66:
        return "warnung", "yellow"
    else:
        return "kritisch", "red"

# ---------------------------------------------------------------------
# Mapping: country_presets.json → Slider-Preset
# ---------------------------------------------------------------------

def country_to_slider_preset(code: str, country_preset: dict) -> dict:
    slider = {k: default for (k, _lo, _hi, default) in PARAM_SLIDERS}
    snap = country_preset.get("indicator_snapshot", {}) or {}

    # Verschuldung
    try:
        debt = snap.get("DT_DOD_DECT_CD", {}).get("value")
        gdp = snap.get("NY_GDP_MKTP_CD", {}).get("value")
        if debt and gdp:
            ratio = float(debt) / float(gdp)
            slider["verschuldung"] = normalize_ratio(ratio, 0.0, 2.0) * 2.0
    except:
        pass

    # Reserven
    try:
        res = snap.get("FI_RES_TOTL_MO", {}).get("value")
        if res is not None:
            slider["Reserven_Monate"] = max(0.0, min(24.0, float(res)))
    except:
        pass

    # Offenheit
    try:
        exports = snap.get("NE_EXP_GNFS_CD", {}).get("value")
        imports = snap.get("NE_IMP_GNFS_CD", {}).get("value")
        if exports and imports:
            openness = normalize_log(exports + imports, 9.0, 13.0)
            slider["Zugangsresilienz"] = clamp01(openness)
    except:
        pass

    # Inflation
    try:
        infl = snap.get("FP_CPI_TOTL_ZG", {}).get("value")
        if infl is not None:
            inf_norm = normalize_inflation(infl, 0.0, 10.0)
            slider["FX_Schockempfindlichkeit"] = 0.5 + 1.0 * inf_norm
    except:
        pass

    # Staatsausgabenquote
    try:
        spend = snap.get("GC_XPN_TOTL_GD_ZS", {}).get("value")
        if spend is not None:
            spend_norm = normalize_ratio(spend / 100.0, 0.0, 0.6)
            slider["stabilitaet"] = clamp01(1.0 - 0.7 * spend_norm)
    except:
        pass

    # korruption → Default 0.3 (falls kein Indikator existiert)
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
