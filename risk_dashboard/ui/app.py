# ui/app.py

import sys
sys.path.append("/content/makro_sim/risk_dashboard")

import gradio as gr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
from pathlib import Path


from core.country_assets import (
    compute_country_asset_expectations,
    portfolio_metrics,
    monte_carlo_portfolio,
    build_cov_matrix,
    etf_mapping_for_cluster,
    investment_profile_for_cluster,
)

from core.portfolio_sim.mc_engine import run_portfolio_mc
from core.portfolio_sim.risk_metricks import mc_risk_metrics
from core.data_import import load_returns_csv
from core.portfolio_sim.covariance import compute_covariance, build_asset_covariance
from core.scenario_engine import scenario_by_name
from core.mc_simulator import multi_period_mc, summarize_paths
from test.example_presets import EXAMPLE_PRESETS, CLUSTERS, MODEL

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
from core.cluster import ( 
    cluster_heatmap, 
    describe_clusters, 
    cluster_risk_dimensions, 
    cluster_scatterplot, 
    investment_profile_for_cluster, 
    cluster_radar_plot,
    aktienrendite,
    goldrendite,
    laender_investment_profil,
    laender_radar_plot,
    laender_dashboard,
    portfolio_simulator,
    asset_klassen_vergleich
)
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


DATA_PATH = "/content/makro_sim/risk_dashboard/data"

equity_df = load_returns_csv(
    f"{DATA_PATH}/equity_returns.csv",
    expected_assets=["USA", "Germany", "India", "Brazil", "SouthAfrica"]
)

bond_df = load_returns_csv(
    f"{DATA_PATH}/bond_returns.csv",
    expected_assets=["USA", "Germany", "India", "Brazil", "SouthAfrica"]
)

gold_df = load_returns_csv(
    f"{DATA_PATH}/gold_returns.csv",
    expected_assets=["Gold"]
)


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

    centers = model.cluster_centers_
    inv_profiles = []

    for cid, center in enumerate(centers):
        ps, aut, total = center
        profile_md = investment_profile_for_cluster(ps, aut, total)
        inv_profiles.append(f"## Cluster {cid}\n\n{profile_md}")

    inv_markdown = "\n\n---\n\n".join(inv_profiles)

    radar_fig = cluster_radar_plot(model)
    return rows, fig, lexikon, inv_markdown, radar_fig

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

def run_multi_period_simulation(land, w_equity, w_bond, w_gold, years, scenario_name):
    presets = load_presets()
    sim, summary, fig, fig2 = run_portfolio_mc(
        land, presets, w_equity, w_bond, w_gold, years, scenario_name
    )
    metrics = mc_risk_metrics(sim)

    md = "**Portfolio-Risikoanalyse:**\n\n"
    md += f"- Erwartete Gesamtrendite: {metrics['mean']*100:.2f}%\n"
    md += f"- Volatilität: {metrics['std']*100:.2f}%\n"
    md += f"- Sharpe Ratio: {metrics['sharpe']:.2f}\n"
    md += f"- VaR 95%: {metrics['var95']*100:.2f}%\n"
    md += f"- CVaR 95%: {metrics['cvar95']*100:.2f}%\n"
    md += f"- Max. Drawdown (Ø): {metrics['max_drawdown']*100:.2f}%\n"

    return md, fig, fig2

# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------

def create_gradio_app(presets):

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
            cluster_invest_out = gr.Markdown(label="Investment-Profile nach Cluster")
            radar_out = gr.Plot(label="Cluster-Radar-Chart")

            btn_cluster_complete = gr.Button("Cluster-Analyse starten")
            btn_cluster_complete.click(
                compute_cluster_complete,
                None,
                [cluster_out, scatter_out, cluster_lexikon_out, cluster_invest_out, radar_out]
            )


        with gr.Tab("Rendite-Berechnung"):
            gr.Markdown("## Rendite-Berechnung für Aktien und Gold")
            asset_out = gr.Markdown(label="Asset-Klassen Vergleich")
            btn_asset = gr.Button("Asset-Vergleich anzeigen")
            btn_asset.click(lambda: asset_klassen_vergleich(), None, asset_out)

          
            with gr.Row():
                kurs_alt = gr.Number(label="Aktienkurs (alt)")
                kurs_neu = gr.Number(label="Aktienkurs (neu)")
                dividende = gr.Number(label="Dividende pro Aktie", value=0)

            aktien_out = gr.Markdown(label="Aktienrendite")

            btn_aktie = gr.Button("Aktienrendite berechnen")
            btn_aktie.click(
                aktienrendite,
                [kurs_alt, kurs_neu, dividende],
                aktien_out
            )

            gr.Markdown("---")

            with gr.Row():
                gold_alt = gr.Number(label="Goldpreis (alt)")
                gold_neu = gr.Number(label="Goldpreis (neu)")

            gold_out = gr.Markdown(label="Goldrendite")

            btn_gold = gr.Button("Goldrendite berechnen")
            btn_gold.click(
                goldrendite,
                [gold_alt, gold_neu],
                gold_out
            )

        with gr.Tab("Länder-Investment-Profil"):
            presets = load_presets()
            laender_liste = list(presets.keys())

            land_input = gr.Dropdown(
                choices=laender_liste,
                label="Land auswählen"
            )

            land_dashboard_md = gr.Markdown(label="Länder-Dashboard")
            land_radar_plot = gr.Plot(label="Länder-Radar")
            land_invest_md = gr.Markdown(label="Investment-Profil")

            btn_land = gr.Button("Analyse starten")
            def laender_analyse(land):
                presets = load_presets()
                clusters, model = cluster_risk_dimensions(presets)

                # Dashboard
                cid = clusters[land]
                scores = compute_risk_scores(presets[land])

                dashboard = f"""
# Länder-Dashboard: {land}

**Cluster:** {cid}

## Risiko-Scores
- Politisches Risiko: {scores["political_security"]:.2f}
- Strategische Autonomie: {scores["strategische_autonomie"]:.2f}
- Gesamtrisiko: {scores["total"]:.2f}
"""

                # Investment-Profil
                ps, aut, total = model.cluster_centers_[cid]
                invest = investment_profile_for_cluster(ps, aut, total)

                # Radar-Chart
                radar = laender_radar_plot(land, presets)
                return dashboard, radar, invest

            btn_land.click(
                laender_analyse,
                land_input,
                [land_dashboard_md, land_radar_plot, land_invest_md]
            )

        # --- Portfolio-Simulator ---
        with gr.Tab("Portfolio-Simulator"):
            country_dropdown2 = gr.Dropdown(choices=countries, label="Land auswählen")
            w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
            w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
            w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")

            years = gr.Slider(1, 20, value=10, step=1, label="Anzahl Jahre")
            scenario = gr.Dropdown(
                choices=["Keins", "Krise", "Zinsanstieg", "Ölpreisschock"],
                value="Keins",
                label="Szenario"
            )

            sim_out = gr.Markdown()
            path_plot = gr.Plot()
            terminal_plot = gr.Plot()

            gr.Button("Mehrperioden-Simulation starten").click(
                lambda land, we, wb, wg, yrs, scen: run_multi_period_simulation(
                    land, we, wb, wg, yrs, scen
                ),
                [country_dropdown2, w_equity, w_bond, w_gold, years, scenario],
                [sim_out, path_plot, terminal_plot],
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
