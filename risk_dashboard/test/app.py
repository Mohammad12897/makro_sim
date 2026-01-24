# test/app.py

import sys
sys.path.append("/content/makro_sim/risk_dashboard")

import gradio as gr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- core imports ---
from core.country_assets import (
    compute_country_asset_expectations,
    portfolio_metrics,
    monte_carlo_portfolio,
    build_cov_matrix,
    etf_mapping_for_cluster,
    investment_profile_for_cluster,
)

from core.risk_model import compute_risk_scores

# --- presets ---
from core.example_presets import EXAMPLE_PRESETS, CLUSTERS, MODEL


# ---------------------------------------------------------
# Länder-Übersicht
# ---------------------------------------------------------
def country_overview(land: str, presets: dict):
    data = compute_country_asset_expectations(land, presets)
    scores = data["scores"]

    md = f"# Länder-Asset-Übersicht: {land}\n\n"
    md += f"**Politisches Risiko:** {scores['political_security']:.2f}\n\n"
    md += f"**Strategische Autonomie:** {scores['strategische_autonomie']:.2f}\n\n"
    md += f"**Gesamtrisiko:** {scores['total']:.2f}\n\n"

    md += "## Erwartete Renditen (p.a.)\n"
    md += f"- Aktien: {data['equity_mu']*100:.2f}%\n"
    md += f"- Staatsanleihen (YTM): {data['bond_yield']*100:.2f}%\n"
    md += f"- Gold: {data['gold_mu']*100:.2f}%\n"

    return md


# ---------------------------------------------------------
# Portfolio-Simulation
# ---------------------------------------------------------
def run_portfolio_simulation(land, w_equity, w_bond, w_gold, presets):
    expectations = compute_country_asset_expectations(land, presets)

    mu = np.array([
        expectations["equity_mu"],
        expectations["bond_yield"],
        expectations["gold_mu"],
    ])

    vols = np.array([0.18, 0.06, 0.12])
    corr = np.array([
        [1.0, 0.2, 0.3],
        [0.2, 1.0, 0.1],
        [0.3, 0.1, 1.0],
    ])

    cov = build_cov_matrix(vols, corr)

    weights = np.array([w_equity, w_bond, w_gold])
    weights = weights / weights.sum()

    metrics = portfolio_metrics(weights, mu, cov, rf=0.01)
    mc = monte_carlo_portfolio(weights, mu, cov, n=5000, seed=42)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.hist(mc["sim_returns"], bins=60, color="#2ca02c", alpha=0.6)
    ax.axvline(np.percentile(mc["sim_returns"], 5), color="red", linestyle="--", label="VaR 95%")
    ax.set_title("Simulierte Jahresrenditen (Monte Carlo)")
    ax.set_xlabel("Rendite")
    ax.set_ylabel("Häufigkeit")
    ax.legend()

    md = f"**Erwartete Portfolio-Rendite:** {metrics['mu']*100:.2f}%\n\n"
    md += f"**Portfolio-Volatilität:** {metrics['sigma']*100:.2f}%\n\n"
    md += f"**Sharpe Ratio:** {metrics['sharpe']:.2f}\n\n"
    md += f"**Simulationsmittel:** {mc['sim_mean']*100:.2f}%\n"
    md += f"**VaR 95%:** {mc['var95']*100:.2f}%\n"
    md += f"**CVaR 95%:** {mc['cvar95']*100:.2f}%\n"

    return md, fig


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------
def create_gradio_app(presets):
    countries = sorted(list(presets.keys()))

    with gr.Blocks() as demo:
        gr.Markdown("# Länderbezogene Asset-Analyse & Portfolio-Simulator")

        # --- Länder-Analyse ---
        with gr.Tab("Länder-Analyse"):
            country_dropdown = gr.Dropdown(choices=countries, label="Land auswählen")
            overview_md = gr.Markdown()
            invest_md = gr.Markdown()
            etf_md = gr.Markdown()

            def on_show(land):
                ov = country_overview(land, presets)
                cid = presets[land].get("cluster", None)
                invest = investment_profile_for_cluster(*MODEL.cluster_centers_[cid])
                etf = etf_mapping_for_cluster(cid)
                return ov, invest, etf

            gr.Button("Übersicht anzeigen").click(
                on_show, country_dropdown, [overview_md, invest_md, etf_md]
            )

        # --- Portfolio-Simulator ---
        with gr.Tab("Portfolio-Simulator"):
            country_dropdown2 = gr.Dropdown(choices=countries, label="Land auswählen")
            w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
            w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
            w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")

            sim_out = gr.Markdown()
            hist_plot = gr.Plot()

            gr.Button("Simuliere Portfolio").click(
                lambda land, we, wb, wg: run_portfolio_simulation(land, we, wb, wg, presets),
                [country_dropdown2, w_equity, w_bond, w_gold],
                [sim_out, hist_plot],
            )

    return demo


if __name__ == "__main__":
    app = create_gradio_app(EXAMPLE_PRESETS)
    app.launch(share=True)
