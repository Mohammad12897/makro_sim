#core/portfolio_sim/plots.py
import numpy as np
import matplotlib.pyplot as plt

def plot_fan_chart(sim):
    paths = sim["paths"]
    years = paths.shape[1]

    percentiles = [5, 25, 50, 75, 95]
    bands = {p: np.percentile(paths, p, axis=0) for p in percentiles}

    fig, ax = plt.subplots(figsize=(6, 3))

    ax.plot(bands[50], color="black", label="Median")
    ax.fill_between(range(years), bands[25], bands[75], color="blue", alpha=0.3, label="50% Band")
    ax.fill_between(range(years), bands[5], bands[95], color="blue", alpha=0.15, label="90% Band")

    ax.set_title("Monte-Carlo Fan Chart")
    ax.set_xlabel("Jahr")
    ax.set_ylabel("Portfolio-Wert")
    ax.legend()

    return fig

def plot_drawdown(sim):
    paths = sim["paths"]
    peak = np.maximum.accumulate(paths, axis=1)
    dd = (peak - paths) / peak

    avg_dd = dd.mean(axis=0)
    worst_dd = dd.max(axis=0)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(avg_dd, label="Durchschnittlicher Drawdown", color="red")
    ax.plot(worst_dd, label="Worst-Case Drawdown", color="black", linestyle="--")

    ax.set_title("Drawdown-Analyse")
    ax.set_xlabel("Jahr")
    ax.set_ylabel("Drawdown")
    ax.legend()

    return fig

def plot_portfolio_radar(metrics):
    labels = ["Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"]
    values = [
        metrics["mean"],
        metrics["std"],
        metrics["sharpe"],
        metrics["var95"],
        metrics["cvar95"],
        metrics["max_drawdown"],
    ]

    values = [abs(v) for v in values]
    values.append(values[0])

    angles = np.linspace(0, 2 * np.pi, len(values))

    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111, polar=True)

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    ax.set_title("Portfolio Risiko-Radar")

    return fig

def plot_path_plot(summary):
    fig, ax = plt.subplots(figsize=(6, 3))

    ax.plot(summary["year"], summary["mean"], label="Erwartete Rendite", color="blue")
    ax.plot(summary["year"], summary["var95"], label="VaR 95%", color="red", linestyle="--")

    ax.set_xlabel("Jahr")
    ax.set_ylabel("Rendite")
    ax.set_title("Mehrperioden-Simulation")
    ax.legend()

    return fig

def plot_terminal_distribution(sim):
    fig, ax = plt.subplots(figsize=(6, 3))

    ax.hist(sim["terminal_distribution"], bins=60, color="#2ca02c", alpha=0.6)
    ax.set_title("Verteilung der Gesamtrendite (Endwert)")
    ax.set_xlabel("Gesamtrendite")
    ax.set_ylabel("Häufigkeit")

    return fig

def plot_scenario_radar_overlay(scenario_metrics: dict):
    """
    scenario_metrics: {szenario_name: metrics_dict}
    """
    import plotly.graph_objects as go

    categories = ["mean", "std", "sharpe", "var95", "max_drawdown"]

    fig = go.Figure()

    for scen, m in scenario_metrics.items():
        values = [m[c] for c in categories]
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=scen
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title="Szenario-Radar-Overlay"
    )
    return fig
