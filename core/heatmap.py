# core/heatmap.py

from __future__ import annotations
import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from core.risk_model import compute_risk_scores

def classify_risk(score):
    if score < 0.33:
        return "stabil", "green"
    elif score < 0.66:
        return "warnung", "yellow"
    else:
        return "kritisch", "red"

def risk_heatmap(countries: dict):
    table = []

    for code, params in countries.items():
        scores = compute_risk_scores(params)

        row = {
            "land": code,
            "macro": scores["macro"],
            "macro_color": classify_risk(scores["macro"])[1],
            "geo": scores["geo"],
            "geo_color": classify_risk(scores["geo"])[1],
            "gov": scores["governance"],
            "gov_color": classify_risk(scores["governance"])[1],
            "total": scores["total"],
            "total_color": classify_risk(scores["total"])[1],
        }

        table.append(row)

    return table
