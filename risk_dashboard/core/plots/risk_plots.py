#core/plots/risk_plots.py
import numpy as np
import matplotlib.pyplot as plt

COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c",
    "#d62728", "#9467bd", "#8c564b"
]

def normalize(values):
    arr = np.array(values, dtype=float)
    min_v, max_v = arr.min(), arr.max()
    if max_v - min_v == 0:
        return np.zeros_like(arr)
    return (arr - min_v) / (max_v - min_v)

def plot_scenario_radar_overlay(metrics):
    """
    metrics: dict {
        "baseline": {"inflation": 0.2, "gdp": -0.1, ...},
        "shock1":   {"inflation": 0.5, "gdp": -0.4, ...}
    }
    """

    # --- Einheitliche Indikatorenliste ---
    first_scen = next(iter(metrics.values()))
    labels = list(first_scen.keys())
    num_vars = len(labels)

    # --- Winkel berechnen ---
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles.append(angles[0])  # Kreis schließen

    # --- Plot ---
    fig = plt.figure(figsize=(7, 7))
    ax = plt.subplot(111, polar=True)

    for i, (scen_name, values) in enumerate(metrics.items()):
        # Werte in exakt derselben Reihenfolge extrahieren
        vals = [values[k] for k in labels]

        # Normieren
        vals = normalize(vals)

        # Kreis schließen
        vals = vals.tolist()
        vals.append(vals[0])

        color = COLORS[i % len(COLORS)]

        ax.plot(angles, vals, linewidth=2.2, color=color, label=scen_name)
        ax.scatter(angles, vals, color=color, s=40)
        ax.fill(angles, vals, color=color, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_yticklabels([])

    ax.set_title("Risiko‑Radar (normiert)", fontsize=14, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return fig
