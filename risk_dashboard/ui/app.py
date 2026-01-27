# ui/app.py

import sys
sys.path.append("/content/makro_sim/risk_dashboard")

import gradio as gr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
from pathlib import Path

theme = gr.themes.Soft(primary_hue="blue", secondary_hue="slate")

from core.country_assets import (
    portfolio_metrics,
    monte_carlo_portfolio,
    build_cov_matrix,
    etf_mapping_for_cluster,
    investment_profile_for_cluster,
)

from core.portfolio_sim.plots import (
    plot_path_plot,
    plot_terminal_distribution,
    plot_fan_chart,
    plot_drawdown,
    plot_portfolio_radar,
    plot_scenario_radar_overlay,
)

from core.scenario_engine import (
    scenario_by_name,
    RISK_SCENARIOS,
    apply_risk_scenario, 
    scenario_radar_overlay,
)

from core.portfolio_sim.risk_metrics import mc_risk_metrics

from core.portfolio_sim.scenario_compare import run_scenario_comparison
from core.data_import import load_returns_csv
from core.portfolio_sim.covariance import compute_covariance, build_asset_covariance
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
from core.lexicon import load_lexicon
from core.storyline import storyline_v3
from core.ews import ews_for_country
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


def update_krise_params(eq, bo, go):
    SCENARIO_CONFIG["Krise"]["mu_shift"][0] = eq
    SCENARIO_CONFIG["Krise"]["mu_shift"][1] = bo
    SCENARIO_CONFIG["Krise"]["mu_shift"][2] = go
    return f"**Krise aktualisiert:** Equity={eq}, Bonds={bo}, Gold={go}"

def update_zins_params(eq, bo, go):
    SCENARIO_CONFIG["Zinsanstieg"]["mu_shift"][0] = eq
    SCENARIO_CONFIG["Zinsanstieg"]["mu_shift"][1] = bo
    SCENARIO_CONFIG["Zinsanstieg"]["mu_shift"][2] = go
    return f"**Zinsanstieg aktualisiert:** Equity={eq}, Bonds={bo}, Gold={go}"

def update_oil_params(eq, bo, go):
    SCENARIO_CONFIG["Ölpreisschock"]["mu_shift"][0] = eq
    SCENARIO_CONFIG["Ölpreisschock"]["mu_shift"][1] = bo
    SCENARIO_CONFIG["Ölpreisschock"]["mu_shift"][2] = go
    return f"**Ölpreisschock aktualisiert:** Equity={eq}, Bonds={bo}, Gold={go}"


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


def apply_shocks_to_scores(base_scores, shock_values):
    """
    Wendet Szenario-Shocks auf die Risiko-Scores an.
    Alle Werte werden auf [0, 1] begrenzt.
    """

    new_scores = {}

    for key, value in base_scores.items():
        shock = shock_values.get(key, 0.0)
        new_scores[key] = max(0.0, min(1.0, value + shock))

    return new_scores

def compute_scenario_scores(params, shock_values=None):
    """
    Berechnet Szenario-Risiko-Scores direkt aus den Slider-Presets,
    ohne Monte-Carlo-Portfolio-Simulation.
    """

    presets = params["presets"]  # das ist der Eintrag aus slider_presets.json

    # Baseline-Risiko aus den Slidern
    base_scores = compute_risk_scores(presets)

    # Falls du shock_values schon hast und anwenden willst:
    if shock_values is None:
        return base_scores

    scenario_scores = apply_shocks_to_scores(base_scores, shock_values)
    return scenario_scores

def compute_scenario(country, scenario_name):

    presets = load_presets()
    scenarios = load_scenarios()

    # Preset-Daten für das Land
    preset_params = presets[country]

    # Events → Shocks
    events = scenarios[scenario_name]
    shock_values = convert_events_to_shocks(events)

    # Szenario-Parameter für compute_scenario_scores()
    params = {
        "land": country,
        "presets": preset_params,
        "weights": [50, 30, 20],   # oder aus UI
        "years": 10,               # oder aus UI
        "scenario": scenario_name,
    }

    # Baseline
    base_scores = compute_risk_scores(preset_params)

    # Szenario
    scenario_scores = compute_scenario_scores(params, shock_values)

    # Plot
    fig = make_delta_radar_plot(
        base_scores,
        scenario_scores,
        title=f"Szenario: {scenario_name}"
    )

    if isinstance(fig, (list, tuple)):
        fig = fig[0]

    return fig


def compute_scenario_plot(country, scenario_name):

    presets_all = load_presets()          # lädt slider_presets.json
    scenarios = load_scenarios()          # deine Szenario-Definitionen

    preset_params = presets_all[country]  # das Dict mit verschuldung, energie, ...

    events = scenarios[scenario_name]
    shock_values = convert_events_to_shocks(events)

    # Baseline
    base_scores = compute_risk_scores(preset_params)

    # Szenario
    params = {
        "land": country,
        "presets": preset_params,
        "scenario": scenario_name,
    }
    scenario_scores = compute_scenario_scores(params, shock_values)

    fig = make_delta_radar_plot(
        base_scores,
        scenario_scores,
        title=f"Szenario: {scenario_name}"
    )

    return fig

def make_decision_support_text(risk_scores):
    lex = load_lexicon()

    lines = []
    lines.append("## 🧭 Decision Support Analyse\n")

    # Beispiel: Risiko-Dimensionen interpretieren
    for dim, value in risk_scores.items():
        if dim in lex:
            explanation = lex[dim]
        else:
            explanation = "Keine Beschreibung verfügbar."

        if value > 0.7:
            level = "🔴 Hoch"
        elif value > 0.4:
            level = "🟠 Mittel"
        else:
            level = "🟢 Niedrig"

        lines.append(f"### {dim} — {level}")
        lines.append(f"{explanation}")
        lines.append(f"**Score:** {value:.2f}\n")

    return "\n".join(lines)

def compute_decision_support(country):
    presets = load_presets()
    params = presets[country]
    text = make_decision_support_text(params)
    return text

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

def compute_radar_overlay(land, we, wb, wg, yrs):
    presets_all = load_presets()
    base_scores = presets_all[land]

    # Risiko-Szenarien anwenden (MC-frei)
    metrics = scenario_radar_overlay(base_scores)

    fig = plot_scenario_radar_overlay(metrics)
    return fig

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
        #scen_scores = run_scenario(params, shock_values)
        scen_scores = compute_scenario_scores(params, shock_values)

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

def run_multi_period_simulation(*args, **kwargs):
    return (
        "Portfolio-Simulator ist deaktiviert (Option A).",
        None, None, None, None, None
    )

# ---------------------------------------------------------
# Gradio App
# ---------------------------------------------------------


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
        gr.Markdown("## 📊 Szenario-Analyse")

        country_s = make_country_dropdown(countries)
        scenario_s = make_scenario_dropdown(scenario_names)

        scen_radar_out = gr.Plot()
        scen_decision_out = gr.Markdown()

        btn_scen = gr.Button("Szenario (Delta-Radar) ausführen")
        btn_decision = gr.Button("Decision Support")

        btn_scen.click(
            compute_scenario_plot,
            [country_s, scenario_s],
            scen_radar_out
        )

        btn_decision.click(
            compute_decision_support,
            [country_s],
            scen_decision_out
        )

    with gr.Tab("Szenario-Vergleich"):
        scen_country = gr.Dropdown(choices=countries, label="Land")
        scen_w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
        scen_w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
        scen_w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
        scen_years = gr.Slider(1, 20, value=10, step=1, label="Jahre")

        scen_button = gr.Button("Szenarien vergleichen")
        scen_table = gr.Dataframe()

        def _scenario_wrapper(land, we, wb, wg, yrs):
            presets_all = load_presets()
            presets = presets_all[land]

            # weights werden aktuell nicht genutzt, können aber später in shocks einfließen
            return run_scenario_comparison(land, presets, [we, wb, wg], yrs)

        scen_button.click(
            _scenario_wrapper,
            [scen_country, scen_w_equity, scen_w_bond, scen_w_gold, scen_years],
            scen_table
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

        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                country_dropdown2 = gr.Dropdown(choices=countries, label="Land")
                w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
                w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
                w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
                years = gr.Slider(1, 20, value=10, step=1, label="Jahre")
                scenario = gr.Dropdown(
                    choices=["Keins", "Krise", "Zinsanstieg", "Ölpreisschock"],
                    value="Keins",
                    label="Szenario"
                )

                run_button = gr.Button("Simulation starten")

            with gr.Column(scale=2):
                with gr.Tab("KPIs"):
                    gr.Markdown("**Kennzahlen des Portfolios:** Übersicht über Rendite, Risiko und Verlustkennzahlen.")
                    sim_out = gr.Markdown()

                with gr.Tab("Pfad-Plot"):
                    gr.Markdown("**Zeitliche Entwicklung:** Erwartete Entwicklung des Portfolios über die Jahre.")
                    path_plot = gr.Plot()

                with gr.Tab("Terminalverteilung"):
                    gr.Markdown("**Endwert-Verteilung:** Histogramm der simulierten Endwerte nach X Jahren.")
                    terminal_plot = gr.Plot()

                with gr.Tab("Fan Chart"):
                    gr.Markdown("**Unsicherheitsbandbreiten:** Percentile-Bänder (5–95%, 25–75%, Median).")
                    fan_plot = gr.Plot()

                with gr.Tab("Drawdown"):
                    gr.Markdown("**Verlustanalyse:** Durchschnittlicher und schlimmster Drawdown über die Zeit.")
                    dd_plot = gr.Plot()

                with gr.Tab("Portfolio Radar"):
                    gr.Markdown("**Risiko-Profil:** Radar-Diagramm der wichtigsten Risiko- und Performance-Kennzahlen.")
                    radar_plot = gr.Plot()

        run_button.click(
            run_multi_period_simulation,
            [country_dropdown2, w_equity, w_bond, w_gold, years, scenario],
            [sim_out, path_plot, terminal_plot, fan_plot, dd_plot, radar_plot],
        )

    with gr.Tab("Szenario‑Parameter"):
        gr.Markdown("## 🔧 Szenario‑Parameter konfigurieren")

        # --- Krise ---
        gr.Markdown("### Krise")

        krise_equity_shift = gr.Slider(-0.2, 0.0, value=-0.08, label="Equity‑Shift")
        krise_bond_shift = gr.Slider(-0.2, 0.2, value=-0.02, label="Bond‑Shift")
        krise_gold_shift = gr.Slider(0.0, 0.2, value=0.03, label="Gold‑Shift")

        btn_update_krise = gr.Button("Krise‑Parameter aktualisieren")
        out_krise = gr.Markdown()

        # --- Zinsanstieg ---
        gr.Markdown("### Zinsanstieg")

        zins_equity_shift = gr.Slider(-0.2, 0.2, value=-0.02, label="Equity‑Shift")
        zins_bond_shift = gr.Slider(-0.2, 0.2, value=0.03, label="Bond‑Shift")
        zins_gold_shift = gr.Slider(-0.2, 0.2, value=0.00, label="Gold‑Shift")

        btn_update_zins = gr.Button("Zinsanstieg‑Parameter aktualisieren")
        out_zins = gr.Markdown()

        # --- Ölpreisschock ---
        gr.Markdown("### Ölpreisschock")

        oil_equity_shift = gr.Slider(-0.2, 0.2, value=-0.03, label="Equity‑Shift")
        oil_bond_shift = gr.Slider(-0.2, 0.2, value=0.00, label="Bond‑Shift")
        oil_gold_shift = gr.Slider(0.0, 0.3, value=0.05, label="Gold‑Shift")

        btn_update_oil = gr.Button("Ölpreisschock‑Parameter aktualisieren")
        out_oil = gr.Markdown()

        btn_update_krise.click(
            update_krise_params,
            [krise_equity_shift, krise_bond_shift, krise_gold_shift],
            out_krise
        )

        btn_update_zins.click(
            update_zins_params,
            [zins_equity_shift, zins_bond_shift, zins_gold_shift],
            out_zins
        )

        btn_update_oil.click(
            update_oil_params,
            [oil_equity_shift, oil_bond_shift, oil_gold_shift],
            out_oil
        )

    with gr.Tab("Szenario‑Radar‑Overlay"):

        gr.Markdown("## 📊 Szenario‑Radar‑Overlay")

        radar_country = gr.Dropdown(choices=countries, label="Land")
        radar_w_equity = gr.Slider(0, 100, value=50, label="Equity (%)")
        radar_w_bond = gr.Slider(0, 100, value=30, label="Bonds (%)")
        radar_w_gold = gr.Slider(0, 100, value=20, label="Gold (%)")
        radar_years = gr.Slider(1, 20, value=10, step=1, label="Jahre")

        btn_radar = gr.Button("Radar‑Overlay erzeugen")

        radar_plot_out = gr.Plot(label="Radar‑Overlay")
        btn_radar.click(
            compute_radar_overlay,
            [radar_country, radar_w_equity, radar_w_bond, radar_w_gold, radar_years],
            radar_plot_out
        )

    with gr.Tab("Cluster‑Lexikon"):
        lexikon_md = gr.Markdown()

        def show_lexikon():
            lex = load_lexicon()
            text = "\n\n".join([f"### {k}\n{v}" for k, v in lex.items()])
            return text

        btn_show_lexikon = gr.Button("Lexikon anzeigen")
        btn_show_lexikon.click(show_lexikon, None, lexikon_md)

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

__all__ = ["app", "theme"]
