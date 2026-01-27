# core/plots/risk_plots.py

import numpy as np
import matplotlib.pyplot as plt

def plot_scenario_radar_overlay(metrics):
    """
    Zeichnet ein Radar-Overlay für Risiko-Szenarien.
    metrics: dict {szenario_name: {indikator: wert}}
    """

    first_scen = next(iter(metrics.values()))
    labels = list(first_scen.keys())

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(6, 6))
    ax = plt.subplot(111, polar=True)

    for scen_name, values in metrics.items():
        vals = list(values.values())
        vals += vals[:1]

        ax.plot(angles, vals, linewidth=2, label=scen_name)
        ax.fill(angles, vals, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.set_title("Radar-Overlay der Risiko-Szenarien")

    return fig
