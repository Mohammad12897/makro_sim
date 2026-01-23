# ui/app.py

import gradio as gr
import json
from pathlib import Path

from core.shock_mapping import convert_events_to_shocks
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
from core.cluster import cluster_heatmap, describe_clusters, cluster_risk_dimensions, cluster_scatterplot
from core.scenario_engine import rank_countries
from core.utils import load_presets, load_scenarios

from ui.components import (
    make_radar_plot,
    make_multi_radar_plot,
    make_country_dropdown,
    make_scenario_dropdown,
    make_delta_radar_plot,
    make_heatmap_radar
)
from ui.plots import plot_radar
from core.scenario_engine import load_lexicon
lex = load_lexicon()


# ---------------------------------------------------------
# Compute-Funktionen (Backend-Wrapper)
# ---------------------------------------------------------

def compute_single_radar_old(country):
    presets = load_presets()
    params = presets[country]
    scores = compute_risk_scores(params)
    return make_radar_plot(scores, title=f"Risiko-Radar – {country}")

def compute_single_radar(country):
    presets = load_presets()
    params = presets[country]
    scores = compute_risk_scores(params)

    fig = make_radar_plot(scores, title=f"Risiko-Radar – {country}")

    if isinstance(fig, list):
        fig = fig[0]
    if isinstance(fig, tuple):
        fig = fig[0]

    return fig

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
    events = scenarios[scenario_name]

    # Events → Risiko-Shocks
    shock_values = convert_events_to_shocks(events)

    # Baseline
    base_scores = compute_risk_scores(params)

    # Szenario
    scenario_scores = run_scenario(params, shock_values)

    # Plot erzeugen
    fig = make_delta_radar_plot(
        base_scores,
        scenario_scores,
        title=f"Szenario: {scenario_name}"
    )

    # Falls make_delta_radar_plot eine Liste zurückgibt → erste Figur nehmen
    if isinstance(fig, list):
        fig = fig[0]
    if isinstance(fig, tuple):
        fig = fig[0]

    return fig


def compute_decision_support(country):
    presets = load_presets()
    scenarios = load_scenarios()
    return decision_support_view(presets[country], scenarios)


def compute_cluster():
    presets = load_presets()
    clusters, _ = cluster_risk_dimensions(presets, k=3)

    # Tabelle (Dataframe) für Cluster-Zuordnung
    rows = cluster_heatmap(presets)

    # Lexikon als Markdown
    lexikon = describe_clusters(presets, clusters)

    return rows, lexikon


def compute_cluster_complete():
    presets = load_presets()

    # Clustering durchführen
    clusters, model = cluster_risk_dimensions(presets, k=3)

    # Tabelle
    rows = cluster_heatmap(presets)

    # Scatterplot
    fig = cluster_scatterplot(presets, k=3)

    # Lexikon (mit Modell!)
    lexikon = describe_clusters(presets, clusters, model)

    return rows, fig, lexikon

def compute_heatmap_radar(country):
    presets = load_presets()
    scores = compute_risk_scores(presets[country])

    fig = make_heatmap_radar(scores, title=f"Heatmap-Radar – {country}")

    if isinstance(fig, list):
        fig = fig[0]
    if isinstance(fig, tuple):
        fig = fig[0]

    return fig

def compute_scenario_comparison(country, scenario_names):
    presets = load_presets()
    scenarios = load_scenarios()
    params = presets[country]

    base_scores = compute_risk_scores(params)
    base_avg = sum(base_scores.values()) / len(base_scores)

    results = []

    for name in scenario_names:
        events = scenarios[name]
        shock_values = convert_events_to_shocks(events)
        scen_scores = run_scenario(params, shock_values)

        scen_avg = sum(scen_scores.values()) / len(scen_scores)
        delta = scen_avg - base_avg
        results.append((name, scen_avg, delta))

    results.sort(key=lambda x: x[2], reverse=True)

    def arrow(d):
        if d > 0:
            return "▲"
        elif d < 0:
            return "▼"
        return "■"

    def color(v):
        if v < 0.33:
            return "🟢"
        elif v < 0.66:
            return "🟡"
        return "🔴"

    lines = [f"# Szenario-Vergleich – {country}", ""]
    lines.append(f"**Baseline Ø-Risiko:** {base_avg:.2f}")
    lines.append("")

    lines.append("## Ranking der Szenarien (nach Risikoanstieg)")
    lines.append("")

    for name, avg, delta in results:
        lines.append(
            f"- **{name}:** Ø {avg:.2f} {color(avg)} "
            f"({arrow(delta)} {delta:+.2f})"
        )

    return "\n".join(lines)

def compute_risk_cockpit(country):
    presets = load_presets()
    params = presets[country]
    scores = compute_risk_scores(params)

    def risk_level(v):
        if v < 0.33:
            return "🟢 niedrig"
        elif v < 0.66:
            return "🟡 mittel"
        else:
            return "🔴 hoch"

    mapping = {
        "macro": "Makro",
        "geo": "Geo",
        "governance": "Governance",
        "handel": "Handel",
        "supply_chain": "Lieferkette",
        "financial": "Finanzen",
        "tech": "Tech",
        "energie": "Energie",
        "currency": "Währung",
        "political_security": "Politische Abhängigkeit",
        "strategische_autonomie": "Strategische Autonomie",
    }

    # Sortierung für Top-3
    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top3_risks = sorted_dims[:3]
    top3_strengths = sorted_dims[-3:]

    avg = sum(scores.values()) / len(scores)

    lines = [f"# Risiko-Cockpit – {country}", ""]
    lines.append(f"**Ø-Risiko:** {avg:.2f}")
    lines.append("")

    # Top-3 Risiken
    lines.append("## 🔥 Top‑3 Risiken")
    for key, val in top3_risks:
        lines.append(f"- **{mapping[key]}:** {val:.2f} ({risk_level(val)})")
    lines.append("")

    # Top-3 Stärken
    lines.append("## 🌱 Top‑3 Stärken")
    for key, val in top3_strengths:
        lines.append(f"- **{mapping[key]}:** {val:.2f} ({risk_level(val)})")
    lines.append("")

    # Alle Dimensionen
    lines.append("## Gesamtübersicht")
    for key, label in mapping.items():
        v = scores[key]
        lines.append(f"- {label}: **{v:.2f}** ({risk_level(v)})")

    return "\n".join(lines)


# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def build_app():

    with gr.Blocks(title="Makro Risk Dashboard – Professional Edition") as app:

        gr.Markdown("# 🌍 Makro Risk Dashboard – Professional Edition")

        presets = load_presets()
        countries = list(presets.keys())
        scenarios = load_scenarios()
        scenario_names = list(scenarios.keys())

        with gr.Tab("Länderprofil"):
            country = make_country_dropdown(countries)

            radar_out = gr.Plot()
            storyline_out = gr.Markdown()
            ews_out = gr.Markdown()

            btn_radar = gr.Button("Radar anzeigen")
            btn_story = gr.Button("Storyline erzeugen")
            btn_ews = gr.Button("Early Warning System")

            btn_radar.click(compute_single_radar, country, radar_out)
            btn_story.click(compute_storyline, country, storyline_out)
            btn_ews.click(compute_ews, country, ews_out)

        with gr.Tab("Multi-Radar"):
            country_multi = gr.CheckboxGroup(
                choices=countries,
                label="Länder auswählen",
                value=countries[:3]
            )
            multi_radar_out = gr.Plot()
            btn_multi = gr.Button("Multi-Radar anzeigen")
            btn_multi.click(compute_multi_radar, country_multi, multi_radar_out)

        with gr.Tab("Szenarien"):
            country_s = make_country_dropdown(countries)
            scenario_s = make_scenario_dropdown(scenario_names)

            scen_radar_out = gr.Plot()
            scen_decision_out = gr.Markdown()

            btn_scen = gr.Button("Szenario (Delta-Radar) ausführen")
            btn_decision = gr.Button("Decision Support")

            btn_scen.click(compute_scenario, [country_s, scenario_s], scen_radar_out)
            btn_decision.click(compute_decision_support, country_s, scen_decision_out)

        with gr.Tab("Szenario-Vergleich"):
            country_cmp = make_country_dropdown(countries)
            scenario_cmp = gr.CheckboxGroup(
                choices=scenario_names,
                label="Szenarien auswählen",
                value=scenario_names[:3]
            )
            scen_cmp_out = gr.Markdown()
            btn_cmp = gr.Button("Szenarien vergleichen")
            btn_cmp.click(
                compute_scenario_comparison,
                [country_cmp, scenario_cmp],
                scen_cmp_out
            )

        with gr.Tab("Cluster-Komplettansicht"):
            with gr.Row():
                cluster_out = gr.Dataframe(
                    headers=["Land", "Cluster", "Political Security", "Strategische Autonomie", "Total"],
                    label="Cluster-Zuordnungstabelle"
                )
                scatter_out = gr.Plot(label="Cluster-Visualisierung")

            cluster_lexikon_out = gr.Markdown(label="Cluster-Lexikon")

            btn_cluster_complete = gr.Button("Cluster-Analyse starten")
            btn_cluster_complete.click(
                compute_cluster_complete,
                None,
                [cluster_out, scatter_out, cluster_lexikon_out]
            )


        with gr.Tab("Heatmap-Radar"):
            country_hm = make_country_dropdown(countries)
            heatmap_out = gr.Plot()
            btn_hm = gr.Button("Heatmap-Radar anzeigen")
            btn_hm.click(compute_heatmap_radar, country_hm, heatmap_out)

        with gr.Tab("Risiko-Cockpit"):
            country_cockpit = make_country_dropdown(countries)
            cockpit_out = gr.Markdown()
            btn_cockpit = gr.Button("Cockpit anzeigen")
            btn_cockpit.click(compute_risk_cockpit, country_cockpit, cockpit_out)

    return app

# ---------------------------------------------------------
# Start
# ---------------------------------------------------------

if __name__ == "__main__":
    app = build_app()
    app.launch()
