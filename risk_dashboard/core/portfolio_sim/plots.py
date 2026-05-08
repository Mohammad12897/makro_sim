#core/portfolio_sim/plots.py
import numpy as np
import matplotlib.pyplot as plt
    
# Risiko-basiertes Radar-Overlay (MC-frei)


def plot_scenario_radar_overlay(metrics):
    """
    Zeichnet ein Radar-Overlay für Risiko-Szenarien.
    metrics: dict {szenario_name: {indikator: wert}}
    """

    # Beispiel: metrics = {
    #   "baseline": {"inflation": 0.2, "gdp": -0.1, "unemployment": 0.3},
    #   "shock1":   {"inflation": 0.5, "gdp": -0.4, "unemployment": 0.6},
    # }

    # Indikatoren extrahieren
    first_scen = next(iter(metrics.values()))
    labels = list(first_scen.keys())

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Kreis schließen

    fig = plt.figure(figsize=(6, 6))
    ax = plt.subplot(111, polar=True)

    for scen_name, values in metrics.items():
        vals = list(values.values())
        vals += vals[:1]  # Kreis schließen

        ax.plot(angles, vals, linewidth=2, label=scen_name)
        ax.fill(angles, vals, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.set_title("Radar-Overlay der Risiko-Szenarien")

    return fig
