# ui/app.py

import gradio as gr
import json
from pathlib import Path

from core.risk_model import compute_risk_scores
from core.heatmap import (
    risk_heatmap,
    political_heatmap,
    autonomy_heatmap,
    combined_political_autonomy_heatmap
)
from core.storyline import storyline_v3
from core.ews import ews_for_country
from core.scenario_engine import run_scenario, decision_support_view
from core.cluster import cluster_heatmap

from ui.components import (
    make_radar_plot,
    make_multi_radar_plot,
    make_country_dropdown,
    make_scenario_dropdown
)


# ---------------------------------------------------------
# ROOT-Pfad
# ---------------------------------------------------------

ROOT = Path("/content/makro_sim/risk_dashboard")
PRESET_FILE = ROOT / "data" / "slider_presets.json"
SCENARIO_FILE = ROOT / "data" / "scenario_presets.json"


# ---------------------------------------------------------
# Presets laden
# ---------------------------------------------------------

def load_presets():
    with open(PRESET_FILE, "r") as f:
        return json.load(f)


def load_scenarios():
    with open(SCENARIO_FILE, "r") as f:
        return json.load(f)


# ---------------------------------------------------------
# UI-Funktionen
# ---------------------------------------------------------

def compute_single_radar(country):
    presets = load_presets()
    params = presets[country]
    scores = compute_risk_scores(params)
    return make_radar_plot(scores, title=f"Risiko-Radar – {country}")


def compute_multi_radar(countries):
    presets = load_presets()
    score_list = []
    for c in countries:
        score_list.append((c, compute_risk_scores(presets[c])))
    return make_multi_radar_plot(score_list)


def compute_storyline(country):
    presets = load_presets()
    return storyline_v3(country, presets[country])


def compute_ews(country):
    presets = load_presets()
    return ews_for_country(country, presets[country])


def compute_scenario(country, scenario_name):
    presets = load_presets()
    scenarios = load_scenarios()
    params = presets[country]
    shocks = scenarios[scenario_name]
    scores = run_scenario(params, shocks)
    return make_radar_plot(scores, title=f"Szenario: {scenario_name}")


def compute_decision_support(country):
    presets = load_presets()
    scenarios = load_scenarios()
    return decision_support_view(presets[country], scenarios)


def compute_cluster():
    presets = load_presets()
    return cluster_heatmap(presets, k=3)


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def build_app():

    with gr.Blocks(title="Makro Risk Dashboard") as app:

        gr.Markdown("# 🌍 Makro Risk Dashboard – Professional Edition")

        presets = load_presets()
        countries = list(presets.keys())
        scenarios = load_scenarios()

        # -------------------------------------------------
        # TAB: Länderprofil
        # -------------------------------------------------
        with gr.Tab("Länderprofil"):
            country = make_country_dropdown(countries)

            radar_out = gr.Plot()
            storyline_out = gr.Markdown()
            ews_out = gr.Markdown()

            btn_radar = gr.Button("Radar anzeigen")
            btn_story = gr.Button("Storyline erzeugen")
            btn_ews = gr.Button("EWS anzeigen")

            btn_radar.click(compute_single_radar, country, radar_out)
            btn_story.click(compute_storyline, country, storyline_out)
            btn_ews.click(compute_ews, country, ews_out)

        # -------------------------------------------------
        # TAB: Vergleich
        # -------------------------------------------------
        with gr.Tab("Vergleich"):
            multi_select = gr.CheckboxGroup(countries, label="Länder auswählen")
            multi_radar_out = gr.Plot()
            btn_multi = gr.Button("Vergleich anzeigen")

            btn_multi.click(compute_multi_radar, multi_select, multi_radar_out)

        # -------------------------------------------------
        # TAB: Heatmaps
        # -------------------------------------------------
        with gr.Tab("Heatmaps"):
            heat_out = gr.Dataframe()
            pol_out = gr.Dataframe()
            auto_out = gr.Dataframe()
            comb_out = gr.Dataframe()

            btn_heat = gr.Button("Risiko-Heatmap")
            btn_pol = gr.Button("Politische Abhängigkeit")
            btn_auto = gr.Button("Strategische Autonomie")
            btn_comb = gr.Button("Kombinierte Analyse")

            btn_heat.click(lambda: risk_heatmap(load_presets()), None, heat_out)
            btn_pol.click(lambda: political_heatmap(load_presets()), None, pol_out)
            btn_auto.click(lambda: autonomy_heatmap(load_presets()), None, auto_out)
            btn_comb.click(lambda: combined_political_autonomy_heatmap(load_presets()), None, comb_out)

        # -------------------------------------------------
        # TAB: Szenarien
        # -------------------------------------------------
        with gr.Tab("Szenarien"):
            country_s = make_country_dropdown(countries)
            scenario_s = make_scenario_dropdown(list(scenarios.keys()))

            scen_radar_out = gr.Plot()
            scen_decision_out = gr.Markdown()

            btn_scen = gr.Button("Szenario ausführen")
            btn_decision = gr.Button("Decision Support")

            btn_scen.click(compute_scenario, [country_s, scenario_s], scen_radar_out)
            btn_decision.click(compute_decision_support, country_s, scen_decision_out)

        # -------------------------------------------------
        # TAB: Cluster
        # -------------------------------------------------
        with gr.Tab("Cluster"):
            cluster_out = gr.Dataframe()
            btn_cluster = gr.Button("Cluster berechnen")

            btn_cluster.click(lambda: compute_cluster(), None, cluster_out)

    return app


# ---------------------------------------------------------
# Start
# ---------------------------------------------------------

if __name__ == "__main__":
    app = build_app()
    app.launch()
