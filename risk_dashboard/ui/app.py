# ui/app.py

import gradio as gr
import pandas as pd

from core.presets import load_presets
from core.scenario_engine import scenario_radar_overlay
from core.portfolio_sim.scenario_compare import run_scenario_comparison
from core.plots.risk_plots import plot_scenario_radar_overlay

# ---------------------------------------------------------
# Theme
# ---------------------------------------------------------

theme = gr.themes.Soft()


# ---------------------------------------------------------
# Radar Overlay
# ---------------------------------------------------------

def compute_radar_overlay(land, we, wb, wg, yrs):
    presets_all = load_presets()
    base_scores = presets_all[land]

    metrics = scenario_radar_overlay(base_scores)

    fig = plot_scenario_radar_overlay(metrics)
    return fig


# ---------------------------------------------------------
# Szenario-Vergleich (Tabelle)
# ---------------------------------------------------------

def scenario_table_wrapper(land, we, wb, wg, yrs):
    presets_all = load_presets()
    base_scores = presets_all[land]

    results = run_scenario_comparison(land, base_scores, [we, wb, wg], yrs)

    rows = []
    for scen_name, scores in results.items():
        for key, val in scores.items():
            if isinstance(val, (int, float)):
                rows.append([scen_name, key, val])

    df = pd.DataFrame(rows, columns=["Szenario", "Indikator", "Wert"])
    return df


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def app():

    presets_all = load_presets()
    countries = list(presets_all.keys())  # <-- dynamisch aus JSON

    with gr.Blocks() as demo:

        # ---------------- Radar Overlay ----------------
        with gr.Tab("Radar-Overlay"):
            r_country = gr.Dropdown(choices=countries, label="Land")
            r_w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
            r_w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
            r_w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
            r_years = gr.Slider(1, 20, value=10, step=1, label="Jahre")

            r_button = gr.Button("Radar aktualisieren")
            r_plot = gr.Plot()

            r_button.click(
                compute_radar_overlay,
                [r_country, r_w_equity, r_w_bond, r_w_gold, r_years],
                r_plot,
            )

        # ---------------- Szenario-Vergleich ----------------
        with gr.Tab("Szenario-Vergleich"):
            scen_country = gr.Dropdown(choices=countries, label="Land")
            scen_w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
            scen_w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
            scen_w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
            scen_years = gr.Slider(1, 20, value=10, step=1, label="Jahre")

            scen_button = gr.Button("Szenarien vergleichen")
            scen_table = gr.Dataframe()

            scen_button.click(
                scenario_table_wrapper,
                [scen_country, scen_w_equity, scen_w_bond, scen_w_gold, scen_years],
                scen_table,
            )

    return demo
