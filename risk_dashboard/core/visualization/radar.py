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


def _normalize_values(rows: List[Dict]) -> Dict[str, List[float]]:
    """
    rows: Liste von Dicts (eine Zeile pro Asset, wie aus get_metrics())
    Rückgabe: {ticker: [normierte Werte 0-1 in Reihenfolge RADAR_METRICS]}
    """
    # Rohwerte sammeln
    metric_values = {name: [] for name, _ in RADAR_METRICS}
    for r in rows:
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
    for r in rows:
        ticker = r.get("ticker") or r.get("Ticker")
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

            # Spezialfall Beta: "nah an 1" ist gut
            if name == "Beta":
                # Distanz zu 1, invertiert
                dist = abs(raw - 1.0)
                # je kleiner Distanz, desto besser
                # normieren auf 0–1 über max Distanz im Sample
                max_dist = max(abs(v - 1.0) for v in metric_values[name]) if metric_values[name] else 1.0
                if max_dist == 0:
                    x = 1.0
                else:
                    x = 1.0 - min(dist / max_dist, 1.0)

            # ggf. invertieren, wenn "niedriger = besser"
            if not high_is_good and name != "Beta":
                x = 1.0 - x

            vals.append(x)
        norm[ticker] = vals
    return norm


def plot_radar(rows: List[Dict]):
    """
    rows: Liste von Dicts mit Kennzahlen (mindestens 'Ticker' und die Keys aus RADAR_METRICS)
    Rückgabe: Matplotlib-Figure für Gradio
    """
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center")
        ax.axis("off")
        return fig

    labels = [name for name, _ in RADAR_METRICS]
    num_vars = len(labels)

    # Winkel
    angles = np.linspace(0, 2 * math.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # schließen

    norm = _normalize_values(rows)

    fig, ax = plt.subplots(subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    # Achsenbeschriftung
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])  # keine Radiallabels, nur Form

    # Farben
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown"]

    for i, r in enumerate(rows):
        ticker = r.get("ticker") or r.get("Ticker")
        vals = norm[ticker] + norm[ticker][:1]
        ax.plot(angles, vals, color=colors[i % len(colors)], linewidth=2, label=ticker)
        ax.fill(angles, vals, color=colors[i % len(colors)], alpha=0.15)

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.set_title("Radar-Overlay: Kennzahlenvergleich", pad=20)

    return fig
