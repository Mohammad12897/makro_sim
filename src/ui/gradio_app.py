#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import sys
from pathlib import Path
import json
from typing import List, Dict, Tuple

# --- Projektwurzel zum Python-Pfad hinzufügen ---
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

# --- Core-Module ---
from core.risk_model import compute_risk_scores, risk_category
from core.sensitivity import sensitivity_analysis
from core.heatmap import risk_heatmap
from core.scenario_engine import apply_shock

# --- UI / Plot ---
import gradio as gr
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# PRESETS LADEN
# ============================================================

PRESETS_FILENAME = ROOT.parent / "presets" / "slider_presets.json"

default_params: Dict[str, float] = {
    "USD_Dominanz": 0.7,
    "RMB_Akzeptanz": 0.2,
    "Zugangsresilienz": 0.8,
    "Sanktions_Exposure": 0.05,
    "Alternativnetz_Abdeckung": 0.5,
    "Liquiditaetsaufschlag": 0.03,
    "CBDC_Nutzung": 0.5,
    "Golddeckung": 0.4,
    "innovation": 0.6,
    "fachkraefte": 0.7,
    "energie": 0.5,
    "stabilitaet": 0.9,
    "verschuldung": 0.8,
    "demokratie": 0.8,
    "FX_Schockempfindlichkeit": 0.8,
    "Reserven_Monate": 6,
    "korruption": 0.3,
}

PARAM_SLIDERS: List[Tuple[str, float, float, float]] = [
    ("USD_Dominanz", 0.0, 1.0, default_params["USD_Dominanz"]),
    ("RMB_Akzeptanz", 0.0, 1.0, default_params["RMB_Akzeptanz"]),
    ("Zugangsresilienz", 0.0, 1.0, default_params["Zugangsresilienz"]),
    ("Sanktions_Exposure", 0.0, 1.0, default_params["Sanktions_Exposure"]),
    ("Alternativnetz_Abdeckung", 0.0, 1.0, default_params["Alternativnetz_Abdeckung"]),
    ("Liquiditaetsaufschlag", 0.0, 1.0, default_params["Liquiditaetsaufschlag"]),
    ("CBDC_Nutzung", 0.0, 1.0, default_params["CBDC_Nutzung"]),
    ("Golddeckung", 0.0, 1.0, default_params["Golddeckung"]),
    ("innovation", 0.0, 1.0, default_params["innovation"]),
    ("fachkraefte", 0.0, 1.0, default_params["fachkraefte"]),
    ("energie", 0.0, 1.0, default_params["energie"]),
    ("stabilitaet", 0.0, 1.0, default_params["stabilitaet"]),
    ("verschuldung", 0.0, 2.0, default_params["verschuldung"]),
    ("demokratie", 0.0, 1.0, default_params["demokratie"]),
    ("FX_Schockempfindlichkeit", 0.0, 2.0, default_params["FX_Schockempfindlichkeit"]),
    ("Reserven_Monate", 0, 24, default_params["Reserven_Monate"]),
    ("korruption", 0.0, 1.0, default_params["korruption"]),
]

NUM_SLIDERS = len(PARAM_SLIDERS)


def load_presets() -> dict:
    try:
        text = PRESETS_FILENAME.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            print("Warning: slider_presets.json ist nicht vom Typ dict, setze auf {}.")
            return {}
        return data
    except Exception as e:
        print("Error reading slider_presets.json:", e)
        return {}


presets = load_presets()

# Erwartete Länder-Codes laut deiner Angabe:
EXPECTED_COUNTRIES = ["DE", "US", "IR", "CN", "FR", "IN", "BR", "GR", "GB"]

# ============================================================
# TEXTDATEIEN (Interpretationen) LADEN
# ============================================================

def load_textfile(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "Textdatei konnte nicht geladen werden."


status_radar_text = load_textfile(ROOT.parent / "docs" / "interpretation_status_radar.txt")
delta_radar_text = load_textfile(ROOT.parent / "docs" / "interpretation_delta_radar.txt")
resilienz_radar_text = load_textfile(ROOT.parent / "docs" / "interpretation_resilienz_radar.txt")
heatmap_text = load_textfile(ROOT.parent / "docs" / "interpretation_heatmap.txt")
szenario_text = load_textfile(ROOT.parent / "docs" / "interpretation_szenario.txt")
sensitivitaet_text = load_textfile(ROOT.parent / "docs" / "interpretation_sensitivitaet.txt")
prognose_text = load_textfile(ROOT.parent / "docs" / "interpretation_prognose.txt")
dashboard_text = load_textfile(ROOT.parent / "docs" / "interpretation_dashboard.txt")

# ============================================================
# HILFSFUNKTIONEN FÜR DIE SIMULATION
# ============================================================

def _collect_params_from_values(vals: List[float]) -> Dict[str, float]:
    params = {}
    for (key, _lo, _hi, _default), v in zip(PARAM_SLIDERS, vals):
        params[key] = float(v)
    return params


def build_early_warning(params: Dict[str, float], scores: Dict[str, float]) -> str:
    warnings = []

    total = scores.get("total", 0.0)
    macro = scores.get("macro", 0.0)
    geo = scores.get("geo", 0.0)
    gov = scores.get("governance", 0.0)
    finanz = scores.get("finanz", 0.0)
    sozial = scores.get("sozial", 0.0)

    if total > 0.7:
        warnings.append("Gesamtrisiko im roten Bereich (> 0.7).")
    elif total > 0.5:
        warnings.append("Gesamtrisiko erhöht (> 0.5).")

    if macro > 0.6:
        warnings.append("Makro-Risiko erhöht: Wachstum, Inflation oder Defizite kritisch.")
    if geo > 0.6:
        warnings.append("Geo-Risiko erhöht: geopolitische Spannungen oder Sanktionen möglich.")
    if gov > 0.6:
        warnings.append("Governance-Risiko erhöht: Institutionen, Rechtsstaatlichkeit, Transparenz fragil.")
    if finanz > 0.6:
        warnings.append("Finanz-Risiko erhöht: Finanzsystem oder Schuldenpuffer kritisch.")
    if sozial > 0.6:
        warnings.append("Soziales Risiko erhöht: gesellschaftliche Spannungen möglich.")

    if params.get("verschuldung", 0.0) > 1.2:
        warnings.append("Hohe Verschuldung: Risiko von Refinanzierungsstress.")
    if params.get("FX_Schockempfindlichkeit", 0.0) > 1.2:
        warnings.append("Hohe FX-Schockempfindlichkeit: Währungsrisiko erhöht.")
    if params.get("demokratie", 1.0) < 0.4:
        warnings.append("Niedrige demokratische Qualität: Governance-Risikotreiber.")
    if params.get("korruption", 0.0) > 0.6:
        warnings.append("Hohe Korruption: Governance- und Investitionsrisiko.")

    if not warnings:
        warnings.append("Keine akuten Frühwarnsignale. Situation insgesamt stabil.")

    return "\n".join(f"- {w}" for w in warnings)


# ============================================================
# RADAR-FUNKTIONEN
# ============================================================

def plot_radar(scores: Dict[str, float]):
    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]
    values = [
        scores["macro"],
        scores["geo"],
        scores["governance"],
        scores["finanz"],
        scores["sozial"],
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    values = np.concatenate((values, [values[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Status-Radar")

    return fig


def plot_delta_radar(scores_old: Dict[str, float], scores_new: Dict[str, float]):
    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]

    old_vals = [
        scores_old["macro"],
        scores_old["geo"],
        scores_old["governance"],
        scores_old["finanz"],
        scores_old["sozial"],
    ]

    new_vals = [
        scores_new["macro"],
        scores_new["geo"],
        scores_new["governance"],
        scores_new["finanz"],
        scores_new["sozial"],
    ]

    delta = [n - o for n, o in zip(new_vals, old_vals)]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    delta = np.concatenate((delta, [delta[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, delta, "o-", linewidth=2, color="red")
    ax.fill(angles, delta, alpha=0.25, color="red")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(-1, 1)
    ax.set_title("Delta-Radar (Veränderungen)")

    return fig


def plot_resilience_radar(scores: Dict[str, float]):
    labels = ["Risiko", "Resilienz", "Governance", "Finanz", "Sozial"]
    risk = scores["total"]
    resilience = max(0.0, min(1.0, 1.0 - risk))

    values = [
        risk,
        resilience,
        scores["governance"],
        scores["finanz"],
        scores["sozial"],
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    values = np.concatenate((values, [values[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2, color="green")
    ax.fill(angles, values, alpha=0.25, color="green")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Risiko vs. Resilienz")

    return fig


# ============================================================
# PROGNOSE-FUNKTIONEN
# ============================================================

def forecast(params: Dict[str, float], years: int = 20) -> List[float]:
    results = []
    current = params.copy()

    for _ in range(years):
        current["innovation"] *= 1.01
        current["verschuldung"] *= 1.03
        current["energie"] *= 0.99
        current["demokratie"] *= 0.995

        scores = compute_risk_scores(current)
        results.append(scores["total"])

    return results


def monte_carlo_forecast(
    params: Dict[str, float],
    years: int = 20,
    runs: int = 500,
) -> np.ndarray:
    all_runs = []
    for _ in range(runs):
        current = params.copy()
        values = []
        for _y in range(years):
            current["innovation"] *= np.random.normal(1.01, 0.01)
            current["verschuldung"] *= np.random.normal(1.03, 0.02)
            current["energie"] *= np.random.normal(0.99, 0.01)
            current["demokratie"] *= np.random.normal(0.995, 0.005)
            scores = compute_risk_scores(current)
            values.append(scores["total"])
        all_runs.append(values)
    return np.array(all_runs)


def plot_forecast(values: List[float]):
    fig, ax = plt.subplots()
    ax.plot(values, linewidth=2)
    ax.set_title("Langfrist-Prognose (Deterministisch)")
    ax.set_xlabel("Jahre")
    ax.set_ylabel("Risiko-Score")
    ax.grid(True)
    return fig


def plot_monte_carlo(mc_values: np.ndarray):
    if mc_values.size == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center")
        return fig

    years = mc_values.shape[1]
    x = np.arange(years)

    median = np.median(mc_values, axis=0)
    p05 = np.percentile(mc_values, 5, axis=0)
    p95 = np.percentile(mc_values, 95, axis=0)

    fig, ax = plt.subplots()
    ax.plot(x, median, label="Median", color="blue")
    ax.fill_between(x, p05, p95, color="blue", alpha=0.2, label="5–95% Band")
    ax.set_title("Monte-Carlo-Prognose")
    ax.set_xlabel("Jahre")
    ax.set_ylabel("Risiko-Score")
    ax.legend()
    ax.grid(True)
    return fig


# ============================================================
# UI-FUNKTIONEN (Heatmap, Szenarien, Sensitivität)
# ============================================================

def ui_scenario(country_code, shock_json):
    params = presets[country_code]
    shock = json.loads(shock_json)
    new_params, new_score, report = apply_shock(params, shock)

    table = []
    for r in report:
        table.append([
            r["parameter"],
            r["änderung"],
            r["bedeutung"],
            r["farbe"]
        ])

    return new_score["total"], table


def ui_heatmap():
    table = risk_heatmap(presets)
    rows = []
    for row in table:
        rows.append([
            row["land"],
            row["macro"], row["macro_color"],
            row["geo"], row["geo_color"],
            row["gov"], row["gov_color"],
            row["total"], row["total_color"],
        ])
    return rows


def ui_sensitivity(country_code):
    params = presets[country_code]
    results = sensitivity_analysis(params)

    table = []
    for r in results:
        table.append([
            r["parameter"],
            r["delta"],
            r["bedeutung"],
            r["farbe"],
        ])
    return table


# ============================================================
# UI-FUNKTIONEN – Simulation mit LÄNDER-DROPDOWN
# ============================================================

def load_country_preset(country_code: str) -> List[float]:
    if country_code in presets:
        params = presets[country_code]
    else:
        params = default_params

    values = []
    for key, _lo, _hi, _default in PARAM_SLIDERS:
        values.append(float(params.get(key, default_params[key])))
    return values


def run_simulation_with_radar_and_delta(*vals):
    params = _collect_params_from_values(list(vals))

    scores_new = compute_risk_scores(params)
    scores_old = compute_risk_scores(default_params)

    cat = risk_category(scores_new["total"])
    summary = (
        f"Gesamt-Risiko: {scores_new['total']:.3f} ({cat})\n"
        f"Makro:       {scores_new['macro']:.3f}\n"
        f"Geo:         {scores_new['geo']:.3f}\n"
        f"Governance:  {scores_new['governance']:.3f}\n"
        f"Finanz:      {scores_new['finanz']:.3f}\n"
        f"Sozial:      {scores_new['sozial']:.3f}"
    )

    warning = build_early_warning(params, scores_new)

    fig_radar = plot_radar(scores_new)
    fig_delta = plot_delta_radar(scores_old, scores_new)
    fig_res = plot_resilience_radar(scores_new)

    return summary, warning, fig_radar, fig_delta, fig_res


# ============================================================
# UI – HAUPTANWENDUNG
# ============================================================

with gr.Blocks(title="Makro-Simulation") as demo:

    gr.Markdown("# Makro-Simulation")
    gr.Markdown(
        "Status-Radar, Delta-Radar, Resilienz-Radar, Szenarien, Sensitivität und Langfrist-Prognosen "
        "für makrofinanzielle Risiken."
    )

    with gr.Tabs():

        # ----------------------------------------------------
        # TAB 1 — SIMULATION
        # ----------------------------------------------------
        with gr.Tab("Simulation"):

            gr.Markdown("### Risiko-Simulation mit Frühwarnsystem und Radar-Ansichten")

            country_dropdown = gr.Dropdown(
                choices=[c for c in EXPECTED_COUNTRIES if c in presets.keys()],
                label="Land (für Presets)",
                value=[c for c in EXPECTED_COUNTRIES if c in presets.keys()][0]
                if presets else None,
            )

            slider_components = []
            half = len(PARAM_SLIDERS) // 2

            with gr.Row():
                with gr.Column(scale=2):
                    for key, lo, hi, default in PARAM_SLIDERS[:half]:
                        s = gr.Slider(
                            minimum=lo,
                            maximum=hi,
                            value=default,
                            label=key,
                            step=0.01,
                        )
                        slider_components.append(s)

                with gr.Column(scale=2):
                    for key, lo, hi, default in PARAM_SLIDERS[half:]:
                        s = gr.Slider(
                            minimum=lo,
                            maximum=hi,
                            value=default,
                            label=key,
                            step=0.01,
                        )
                        slider_components.append(s)

            summary_text = gr.Textbox(label="Risiko-Zusammenfassung", lines=6)
            early_warning_box = gr.Textbox(label="Frühwarnindikatoren", lines=8)

            radar_plot = gr.Plot(label="Status-Radar")
            delta_radar_plot = gr.Plot(label="Delta-Radar")
            resilience_radar_plot = gr.Plot(label="Risiko vs. Resilienz")

            with gr.Accordion("Interpretation der Radar-Diagramme", open=False):
                gr.Markdown(f"```\n{status_radar_text}\n```")
                gr.Markdown(f"```\n{delta_radar_text}\n```")
                gr.Markdown(f"```\n{resilienz_radar_text}\n```")

            run_button = gr.Button("Simulation starten")

            country_dropdown.change(
                fn=load_country_preset,
                inputs=[country_dropdown],
                outputs=slider_components,
            )

            run_button.click(
                fn=run_simulation_with_radar_and_delta,
                inputs=slider_components,
                outputs=[
                    summary_text,
                    early_warning_box,
                    radar_plot,
                    delta_radar_plot,
                    resilience_radar_plot,
                ],
            )

        # ----------------------------------------------------
        # TAB 2 — HEATMAP
        # ----------------------------------------------------
        with gr.Tab("Heatmap"):
            gr.Markdown("### Heatmap der Risikotreiber nach Land")

            heat_button = gr.Button("Heatmap erzeugen")
            heat_output = gr.Dataframe(
                headers=[
                    "Land", "Makro", "Makro-Farbe",
                    "Geo", "Geo-Farbe",
                    "Gov", "Gov-Farbe",
                    "Total", "Total-Farbe",
                ],
                wrap=True,
            )

            with gr.Accordion("Interpretation der Radar-Diagramme", open=False):
                gr.Markdown(f"```\n{heatmap_text}\n```")


            heat_button.click(
                fn=ui_heatmap,
                inputs=[],
                outputs=[heat_output],
            )

        # ----------------------------------------------------
        # TAB 3 — SZENARIEN
        # ----------------------------------------------------
        with gr.Tab("Szenarien"):
            gr.Markdown("### Szenario-Engine (Governance-, Makro-, Geo-Schocks)")

            scen_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land",
            )
               
            scen_input = gr.Textbox(
                label="Schock (JSON)",
                value='{"demokratie": -0.2}',
                lines=3,
            )

            scen_button = gr.Button("Szenario anwenden")

            scen_score = gr.Number(label="Neuer Risiko-Score (Total)")
            scen_report = gr.Dataframe(
                headers=["Parameter", "Änderung", "Bedeutung", "Farbe"],
                wrap=True,
            )

            with gr.Accordion("Interpretation der Szenario-Analyse", open=False):
                gr.Markdown(f"```\n{szenario_text}\n```")
 
            scen_button.click(
                fn=ui_scenario,
                inputs=[scen_country, scen_input],
                outputs=[scen_score, scen_report],
            )

        # ----------------------------------------------------
        # TAB 4 — SENSITIVITÄT
        # ----------------------------------------------------
        with gr.Tab("Sensitivität"):
            gr.Markdown("### Sensitivitätsanalyse pro Land")

            sens_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land",
            )

            sens_button = gr.Button("Analyse starten")

            sens_output = gr.Dataframe(
                headers=["Parameter", "Δ Risiko", "Bedeutung", "Farbe"],
                wrap=True,
            )

            with gr.Accordion("Interpretation der Sensitivitätsanalyse", open=False):
                gr.Markdown(f"```\n{sensitivitaet_text}\n```")

            sens_button.click(
                fn=ui_sensitivity,
                inputs=[sens_country],
                outputs=[sens_output],
            )

        # ----------------------------------------------------
        # TAB 5 — PROGNOSE
        # ----------------------------------------------------
        with gr.Tab("Prognose"):
            gr.Markdown("### Langfrist-Prognosen (Deterministisch & Monte-Carlo)")

            prog_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land",
            )

            prog_years = gr.Slider(
                minimum=5,
                maximum=50,
                value=20,
                step=1,
                label="Prognosehorizont (Jahre)",
            )

            prog_runs = gr.Slider(
                minimum=100,
                maximum=2000,
                value=500,
                step=100,
                label="Monte-Carlo Läufe",
            )

            prog_button = gr.Button("Prognose starten")

            prog_plot_det = gr.Plot(label="Deterministische Prognose")
            prog_plot_mc = gr.Plot(label="Monte-Carlo-Prognose")

            def ui_forecast(country, years, runs):
                params = presets[country]
                years = int(years)
                runs = int(runs)

                values = forecast(params, years)
                fig_det = plot_forecast(values)

                mc_vals = monte_carlo_forecast(params, years, runs)
                fig_mc = plot_monte_carlo(mc_vals)

                return fig_det, fig_mc

            with gr.Accordion("Interpretation der Prognose", open=False):
                gr.Markdown(f"```\n{prognose_text}\n```")

            prog_button.click(
                fn=ui_forecast,
                inputs=[prog_country, prog_years, prog_runs],
                outputs=[prog_plot_det, prog_plot_mc],
            )

        
        # ----------------------------------------------------
        # TAB — DASHBOARD
        # ----------------------------------------------------
        with gr.Tab("Dashboard"):

            gr.Markdown("### Gesamtüberblick: Risiko-Dashboard")

            # Land auswählen
            dash_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land",
                value=list(presets.keys())[0],
            )

            # Outputs
            dash_risk_ampel = gr.Markdown()
            dash_radar = gr.Plot()
            dash_resilience = gr.Plot()
            dash_delta = gr.Plot()
            dash_warning = gr.Markdown()
            dash_forecast = gr.Plot()
            dash_heatmap = gr.Dataframe(
                headers=["Land", "Makro", "Makro-Farbe", "Geo", "Geo-Farbe", "Gov", "Gov-Farbe", "Total", "Total-Farbe"],
                wrap=True,
            )

            # Dashboard-Funktion
            def ui_dashboard(country):
                params = presets[country]
                scores = compute_risk_scores(params)
                default_scores = compute_risk_scores(default_params)

                # Ampel
                cat = risk_category(scores["total"])
                ampel = f"### Risiko-Ampel: **{scores['total']:.3f} ({cat})**"

                # Plots
                fig_radar = plot_radar(scores)
                fig_res = plot_resilience_radar(scores)
                fig_delta = plot_delta_radar(default_scores, scores)

                # Frühwarnsystem
                warn = build_early_warning(params, scores)
                warn_md = "### Frühwarnindikatoren\n" + warn.replace("-", "•")

                # Mini-Prognose
                values = forecast(params, years=10)
                fig_forecast = plot_forecast(values)

                # Mini-Heatmap
                table = risk_heatmap(presets)
                rows = []
                for row in table:
                    rows.append([
                    row["land"],
                    row["macro"], row["macro_color"],
                    row["geo"], row["geo_color"],
                    row["gov"], row["gov_color"],
                    row["total"], row["total_color"],
                ])

                return (
                    ampel,
                    fig_radar,
                    fig_res,
                    fig_delta,
                    warn_md,
                    fig_forecast,
                    rows,
                )

            dash_country.change(
                fn=ui_dashboard,
                inputs=[dash_country],
                outputs=[
                    dash_risk_ampel,
                    dash_radar,
                    dash_resilience,
                    dash_delta,
                    dash_warning,
                    dash_forecast,
                    dash_heatmap,
                ],
            )

            # Interpretation
            with gr.Accordion("Interpretation des Dashboards", open=False):
                gr.Markdown(f"```\n{dashboard_text}\n```")
   
        
        # ----------------------------------------------------
        # TAB 6 — METHODIK
        # ----------------------------------------------------
        with gr.Tab("Methodik"):
            gr.Markdown("### Dokumentation der Risiko-Methodik")

            try:
                method_path = ROOT.parent / "docs" / "risk_methodology.md"
                doc_text = method_path.read_text(encoding="utf-8")
            except Exception:
                doc_text = "Dokumentation nicht gefunden."

            gr.Markdown(doc_text)


# ============================================================
# OPTIONAL: Lexikon
# ============================================================

def load_lexikon():
    lexikon_path = ROOT.parent / "docs" / "lexikon_erweitert.md"
    if lexikon_path.exists():
        return lexikon_path.read_text(encoding="utf-8")
    return "Lexikon nicht gefunden."


try:
    lexikon_erweitert_markdown = load_lexikon()
except Exception:
    lexikon_erweitert_markdown = "Lexikon konnte nicht geladen werden."


__all__ = [
    "demo",
    "lexikon_erweitert_markdown",
]

if __name__ == "__main__":
    demo.launch()
