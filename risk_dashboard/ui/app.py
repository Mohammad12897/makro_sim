# ui/app.py

import gradio as gr
import pandas as pd


from core.reporting.pdf_report import create_pdf_report
from core.storyline_engine import (
    generate_storyline,
    generate_executive_summary,
    compute_risk_score,
    risk_color,
)
from core.plots.risk_plots import plot_scenario_radar_overlay
from core.plots.heatmap_plots import plot_risk_heatmap  # falls du Heatmap im PDF willst

from core.presets import load_presets
from core.scenario_engine import scenario_radar_overlay
from core.portfolio_sim.scenario_compare import run_scenario_comparison
from core.plots.risk_plots import plot_scenario_radar_overlay
from core.risk_ampel import compute_risk_score, risk_color
from core.plots.heatmap_plots import plot_risk_heatmap
from core.cluster_engine import compute_clusters


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

    score = compute_risk_score(base_scores)
    ampel = risk_color(score)

    metrics = scenario_radar_overlay(base_scores)
    fig = plot_scenario_radar_overlay(metrics)

    story = generate_storyline(base_scores)
    return ampel, fig, story


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
            r_ampel = gr.Markdown()
            r_plot = gr.Plot()
            r_story = gr.Markdown()


            r_button.click(
                compute_radar_overlay,
                [r_country, r_w_equity, r_w_bond, r_w_gold, r_years],
                [r_ampel, r_plot, r_story],
            )
            pdf_button = gr.Button("PDF exportieren")
            pdf_file = gr.File()

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

        with gr.Tab("Heatmap & Cluster"):
            h_button = gr.Button("Analyse starten")
            h_plot = gr.Plot()
            h_table = gr.Dataframe()

            def run_heatmap_cluster():
                presets_all = load_presets()
                heatmap = plot_risk_heatmap(presets_all)
                clusters = compute_clusters(presets_all)
                return heatmap, clusters

            h_button.click(run_heatmap_cluster, None, [h_plot, h_table])


            pdf_button = gr.Button("PDF exportieren")
            pdf_file = gr.File()

            def export_pdf(land, we, wb, wg, yrs):
                 presets_all = load_presets()
                 base_scores = presets_all[land]

                 score = compute_risk_score(base_scores)
                 ampel = risk_color(score)
                 metrics = scenario_radar_overlay(base_scores)
                 radar_fig = plot_scenario_radar_overlay(metrics)
                 story = generate_storyline(base_scores)
                 summary = generate_executive_summary(base_scores, ampel)

                 # einfache Tabelle aus metrics

                 rows = []
                 for scen_name, scores in metrics.items():
                     for key, val in scores.items():
                         rows.append([scen_name, key, val])
            
                 df = pd.DataFrame(rows, columns=["Szenario", "Indikator", "Wert"])
                 # optional Heatmap für PDF
                 heatmap_fig = plot_risk_heatmap(presets_all)

                 filename = "/tmp/risk_report.pdf"
                 create_pdf_report(
                     filename,
                     land=land,
                     radar_fig=radar_fig,
                     df=df,
                     storyline_text=story,
                     ampel_text=ampel,
                     summary_text=summary,
                     heatmap_fig=heatmap_fig,
                     logo_path=None,  # oder "logo.png", falls vorhanden
                 )
                 return filename

            pdf_button.click(
                export_pdf,
                [r_country, r_w_equity, r_w_bond, r_w_gold, r_years],
                pdf_file
            )

    return demo
