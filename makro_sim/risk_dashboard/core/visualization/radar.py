# core/visualization/radar.py
import math
from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np


# Welche Kennzahlen ins Radar sollen und ob "hoch = gut" oder "niedrig = gut"
RADAR_METRICS = [
    ("1Y %", True),
    ("5Y %", True),
    ("Volatilität %", False),   # niedriger = besser
    ("Sharpe", True),
    ("Max Drawdown %", False),  # niedriger (weniger negativ) = besser
    ("Beta", False),            # näher an 1 = besser -> behandeln wir separat
]


def _normalize_values(rows: Dict[str, Dict]) -> Dict[str, List[float]]:
    """
    rows: dict { ticker: {metric: value} }
    Rückgabe: {ticker: [normierte Werte 0-1 in Reihenfolge RADAR_METRICS]}
    """

    # Rohwerte sammeln
    metric_values = {name: [] for name, _ in RADAR_METRICS}

    for ticker, r in rows.items():
        for name, _ in RADAR_METRICS:
            v = r.get(name)
            if v is not None:
                metric_values[name].append(float(v))

    # Min/Max pro Kennzahl
    metric_minmax = {}
    for name, _ in RADAR_METRICS:
        vals = metric_values[name]
        if not vals:
            metric_minmax[name] = (0.0, 1.0)
        else:
            metric_minmax[name] = (min(vals), max(vals))

    # Normierung 0–1
    norm = {}
    for ticker, r in rows.items():
        vals = []
        for name, high_is_good in RADAR_METRICS:
            raw = r.get(name)
            if raw is None:
                vals.append(0.0)
                continue

            raw = float(raw)
            mn, mx = metric_minmax[name]

            if mx == mn:
                x = 0.5
            else:
                x = (raw - mn) / (mx - mn)

            # Spezialfall Beta
            if name == "Beta":
                dist = abs(raw - 1.0)
                max_dist = max(abs(v - 1.0) for v in metric_values[name]) if metric_values[name] else 1.0
                if max_dist == 0:
                    x = 1.0
                else:
                    x = 1.0 - min(dist / max_dist, 1.0)

            # invertieren falls nötig
            if not high_is_good and name != "Beta":
                x = 1.0 - x

            vals.append(x)

        norm[ticker] = vals

    return norm

def plot_radar(rows):
    """
    rows: dict { ticker: {metric: value} }
    """

    # Sicherheitsprüfung
    for key, val in rows.items():
        if not isinstance(val, dict):
            raise ValueError(f"Radar: Ungültige Faktoren für {key}: {val}")

    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center")
        ax.axis("off")
        return fig

    labels = [name for name, _ in RADAR_METRICS]
    num_vars = len(labels)

    # Winkel
    angles = np.linspace(0, 2 * math.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    # Normalisierte Werte
    norm = _normalize_values(rows)   # rows ist jetzt korrekt!

    fig, ax = plt.subplots(subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])

    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]

    for i, (ticker, vals_dict) in enumerate(rows.items()):
        vals = [float(vals_dict.get(m, 0.0)) for m, _ in RADAR_METRICS]
        vals += vals[:1]

        ax.plot(angles, vals, color=colors[i % len(colors)], linewidth=2, label=ticker)
        ax.fill(angles, vals, color=colors[i % len(colors)], alpha=0.15)

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.set_title("Radar‑Overlay: Kennzahlenvergleich", pad=20)

    return fig
