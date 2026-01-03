# core/scenario_engine.py

from __future__ import annotations
import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from core.risk_model import compute_risk_scores

SHOCK_THRESHOLDS = [
    (0.10, "gering", "green"),
    (0.20, "mittel", "yellow"),
    (0.35, "hoch", "orange"),
    (999, "sehr hoch", "red"),
]

def classify_shock(change):
    change = abs(change)
    for threshold, label, color in SHOCK_THRESHOLDS:
        if change < threshold:
            return label, color

def apply_shock(params: dict, shock: dict):
    new_params = params.copy()
    shock_report = []

    for key, change in shock.items():
        if key not in params:
            continue

        old = params[key]
        new = old * (1 + change)
        new_params[key] = new

        bedeutung, farbe = classify_shock(change)

        shock_report.append({
            "parameter": key,
            "änderung": change,
            "bedeutung": bedeutung,
            "farbe": farbe,
        })

    new_score = compute_risk_scores(new_params)
    return new_params, new_score, shock_report
