# core/sensitivity.py

from __future__ import annotations
import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from core.risk_model import compute_risk_scores, clamp01

SENSITIVITY_THRESHOLDS = [
    (0.02, "gering", "green"),
    (0.05, "mittel", "yellow"),
    (0.10, "hoch", "orange"),
    (999, "sehr hoch", "red"),
]

def classify_delta(delta):
    for threshold, label, color in SENSITIVITY_THRESHOLDS:
        if delta < threshold:
            return label, color

def sensitivity_analysis(params: dict, step: float = 0.1):
    base_score = compute_risk_scores(params)["total"]
    results = []

    for key, value in params.items():
        if not isinstance(value, (int, float)):
            continue

        # +10% Schock
        shocked = params.copy()
        shocked[key] = value * (1 + step)
        new_score = compute_risk_scores(shocked)["total"]

        delta = abs(new_score - base_score)
        bedeutung, farbe = classify_delta(delta)

        results.append({
            "parameter": key,
            "delta": round(delta, 4),
            "bedeutung": bedeutung,
            "farbe": farbe,
        })

    # Sortieren nach Einfluss
    results.sort(key=lambda x: x["delta"], reverse=True)
    return results
