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
from core.risk_model import compute_risk_scores, risk_category, clamp01
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
benchmarking_text = load_textfile(ROOT.parent / "docs" / "interpretation_benchmarking.txt")
handel_lieferketten_text = load_textfile(ROOT.parent / "docs" / "interpretation_handel_lieferketten.txt")
finanzielle_abhaengigkeit_text = load_textfile(ROOT.parent / "docs" / "interpretation_finanzielle_abhaengigkeit.txt") 

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


def build_trade_supply_early_warning(params: dict, scores: dict) -> str:
    lines = []

    # Schwellen auf Score-Ebene
    if scores["handel"] > 0.7:
        lines.append("Kritische Handelsabhängigkeit: hohe Konzentration bei Exporten, Importen oder Handelspartnern.")
    elif scores["handel"] > 0.5:
        lines.append("Erhöhte Handelsabhängigkeit: Diversifizierung sollte geprüft und ausgebaut werden.")

    if scores["supply_chain"] > 0.7:
        lines.append("Kritische Lieferkettenrisiken: hohe Anfälligkeit für Störungen in Produktion und Transport.")
    elif scores["supply_chain"] > 0.5:
        lines.append("Erhöhte Lieferkettenrisiken: Puffer, Alternativrouten und Redundanzen prüfen.")

    # Parameter-spezifische Trigger
    if params.get("chokepoint_abhaengigkeit", 0.5) > 0.7:
        lines.append("Warnsignal: starke Abhängigkeit von wenigen Transportkorridoren oder Seewegen (Chokepoints).")
    if params.get("just_in_time_anteil", 0.5) > 0.7:
        lines.append("Warnsignal: hoher Just-in-Time-Anteil – geringe Lagerpuffer erhöhen Störungsanfälligkeit.")
    if params.get("produktions_konzentration", 0.5) > 0.7:
        lines.append("Warnsignal: Produktion stark in wenigen Ländern/Regionen konzentriert.")
    if params.get("lager_puffer", 0.5) < 0.3:
        lines.append("Warnsignal: sehr geringe Lagerpuffer – Versorgungssicherheit im Krisenfall gefährdet.")

    if not lines:
        return "### Frühwarnsystem Handel & Lieferketten\n\n- Aktuell keine akuten Frühwarnsignale erkannt."

    return "### Frühwarnsystem Handel & Lieferketten\n\n" + "\n".join(f"- {l}" for l in lines)

def build_financial_early_warning(params: dict, scores: dict) -> str:
    lines = []

    if scores["financial"] > 0.7:
        lines.append("Kritische finanzielle Abhängigkeit: hohe Auslandsverschuldung oder starke Kapitalmarktbindung.")
    elif scores["financial"] > 0.5:
        lines.append("Erhöhte finanzielle Abhängigkeit: Kapitalabflüsse oder Zinsanstiege könnten Risiken auslösen.")

    if params.get("auslandsverschuldung", 0.5) > 0.7:
        lines.append("Warnsignal: sehr hohe Auslandsverschuldung.")
    if params.get("kapitalmarkt_abhaengigkeit", 0.5) > 0.7:
        lines.append("Warnsignal: starke Abhängigkeit von internationalen Kapitalmärkten.")
    if params.get("investoren_anteil", 0.5) > 0.7:
        lines.append("Warnsignal: hoher Anteil ausländischer Investoren.")
    if params.get("fremdwaehrungs_refinanzierung", 0.5) > 0.7:
        lines.append("Warnsignal: hohe Refinanzierung in Fremdwährung – anfällig für FX-Schocks.")

    if not lines:
        return "### Frühwarnsystem Finanzielle Abhängigkeit\n\n- Keine akuten Warnsignale."

    return "### Frühwarnsystem Finanzielle Abhängigkeit\n\n" + "\n".join(f"- {l}" for l in lines)


def score_to_traffic_light(score: float) -> str:
    if score < 0.33:
        return "🟢"
    elif score < 0.66:
        return "🟡"
    return "🔴"


def build_early_warning_dashboard(params: Dict[str, float], scores: Dict[str, float]) -> str:
    lines = []
    lines.append("## Frühwarn-Dashboard\n")

    lines.append(f"{score_to_traffic_light(scores['macro'])} Makro-Risiko: {scores['macro']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['geo'])} Geo-Risiko: {scores['geo']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['governance'])} Governance-Risiko: {scores['governance']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['handel'])} Handels-Risiko: {scores['handel']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['supply_chain'])} Lieferketten-Risiko: {scores['supply_chain']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['financial'])} Finanzielle Abhängigkeit: {scores['financial']:.2f}")
    lines.append(f"{score_to_traffic_light(scores['tech'])} Tech-Abhängigkeit: {scores['tech']:.2f}")
    lines.append("")

    if scores["macro"] > 0.66:
        lines.append("- Makro: Kritische Verwundbarkeit – Verschuldung/FX/Reserven prüfen.")
    elif scores["macro"] > 0.5:
        lines.append("- Makro: Erhöhte Risiken – Puffer und Refinanzierung beobachten.")

    if scores["geo"] > 0.66:
        lines.append("- Geo: Hohe geopolitische Spannungen oder Sanktionsrisiken.")
    elif scores["geo"] > 0.5:
        lines.append("- Geo: Relevante Abhängigkeiten von USD oder kritischen Partnern.")

    if scores["governance"] > 0.66:
        lines.append("- Governance: Schwache Institutionen, Korruption oder Fachkräftemangel.")
    elif scores["governance"] > 0.5:
        lines.append("- Governance: Gemischtes Bild – Reformbedarf prüfen.")

    if scores["handel"] > 0.66 or scores["supply_chain"] > 0.66:
        lines.append("- Handel/Lieferketten: Kritische Abhängigkeiten oder fragile Strukturen.")
    elif scores["handel"] > 0.5 or scores["supply_chain"] > 0.5:
        lines.append("- Handel/Lieferketten: Diversifizierung und Puffer ausbauen.")

    if scores["financial"] > 0.66:
        lines.append("- Finanzen: Hohe externe Abhängigkeit – Kapitalabflüsse/Zinsanstiege kritisch.")
    elif scores["financial"] > 0.5:
        lines.append("- Finanzen: Erhöhte externe Verwundbarkeit – Monitoring verstärken.")

    if scores["tech"] > 0.66:
        lines.append("- Technologie: Kritische Abhängigkeit von Hightech-Importen oder Cloud-Infrastruktur.")
    elif scores["tech"] > 0.5:
        lines.append("- Technologie: Erhöhte Verwundbarkeit bei Halbleitern, Software oder Schlüsseltechnologien.")

    if len(lines) == 2:
        lines.append("- Aktuell keine markanten Frühwarnsignale.")

    return "\n".join(lines)

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

def plot_multi_radar(score_dict: dict):
    """
    score_dict = {
        "DE": {"macro":..., "geo":..., ...},
        "US": {...},
        ...
    }
    """
    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    for country, scores in score_dict.items():
        values = [
            scores["macro"],
            scores["geo"],
            scores["governance"],
            scores["finanz"],
            scores["sozial"],
        ]
        values = np.concatenate((values, [values[0]]))
        ax.plot(angles, values, linewidth=2, label=country)
        ax.fill(angles, values, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.set_title("Multi-Radar Vergleich")

    return fig

def plot_handel_radar(params: dict):
    labels = ["Export-Konzentration", "Import kritische Güter", "Partner-Konzentration"]
    values = [
        params.get("export_konzentration", 0.5),
        params.get("import_kritische_gueter", 0.5),
        params.get("partner_konzentration", 0.5),
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Handelsabhängigkeit")
    return fig


def plot_supply_chain_radar(params: dict):
    labels = ["Chokepoints", "Just-in-Time", "Konzentration", "Lagerpuffer"]
    values = [
        params.get("chokepoint_abhaengigkeit", 0.5),
        params.get("just_in_time_anteil", 0.5),
        params.get("produktions_konzentration", 0.5),
        1 - params.get("lager_puffer", 0.5),
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, linewidth=2, color="red")
    ax.fill(angles, values, alpha=0.25, color="red")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Lieferkettenrisiko")
    return fig

def plot_abhaengigkeiten_radar(params: dict):
    labels = [
        "Handel",
        "Lieferketten",
        "Währung/Zahlung",
    ]

    # Aggregierte Scores
    scores = compute_risk_scores(params)
    handel = scores["handel"]
    supply = scores["supply_chain"]

    waehrung = (
        0.5 * clamp01(params.get("USD_Dominanz", 0.7)) +
        0.3 * clamp01(params.get("Sanktions_Exposure", 0.05) * 2.0) +
        0.2 * (1 - clamp01(params.get("Alternativnetz_Abdeckung", 0.5)))
    )
    waehrung = clamp01(waehrung)

    values = [handel, supply, waehrung]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, linewidth=2, color="purple")
    ax.fill(angles, values, alpha=0.25, color="purple")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Abhängigkeiten-Radar")
    return fig

def plot_finanz_radar(params: dict):
    labels = [
        "Auslandsverschuldung",
        "Kapitalmarkt-Abhängigkeit",
        "Investorenanteil",
        "Fremdwährungs-Refinanzierung"
    ]

    values = [
        params.get("auslandsverschuldung", 0.5),
        params.get("kapitalmarkt_abhaengigkeit", 0.5),
        params.get("investoren_anteil", 0.5),
        params.get("fremdwaehrungs_refinanzierung", 0.5),
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, linewidth=2, color="blue")
    ax.fill(angles, values, alpha=0.25, color="blue")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Finanzielle Abhängigkeit")
    return fig

def compute_abhaengigkeiten_block_score(scores: dict) -> float:
    # Einfacher Block: Mittelwert der drei Abhängigkeitsdimensionen
    return (
        scores["handel"] +
        scores["supply_chain"] +
        scores["financial"]
    ) / 3.0


def plot_systemrisiko_radar(params: dict):
    import numpy as np
    import matplotlib.pyplot as plt

    scores = compute_risk_scores(params)

    macro = scores["macro"]
    geo = scores["geo"]
    gov = scores["governance"]
    abhaeng = compute_abhaengigkeiten_block_score(scores)

    labels = ["Makro", "Geo", "Governance", "Abhängigkeiten", "Tech"]
    values = [macro, geo, gov, abhaeng, tech]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, linewidth=2, color="darkred")
    ax.fill(angles, values, alpha=0.25, color="darkred")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Systemrisiko-Radar")
    return fig


def build_trade_supply_feature_matrix(presets: dict):
    countries = []
    X = []
    for land, p in presets.items():
        vec = [
            p.get("export_konzentration", 0.5),
            p.get("import_kritische_gueter", 0.5),
            p.get("partner_konzentration", 0.5),
            p.get("chokepoint_abhaengigkeit", 0.5),
            p.get("just_in_time_anteil", 0.5),
            p.get("produktions_konzentration", 0.5),
            1 - p.get("lager_puffer", 0.5),
        ]
        countries.append(land)
        X.append(vec)
    return countries, X

def build_trade_supply_financial_matrix(presets: dict):
    countries = []
    X = []
    for land, p in presets.items():
        vec = [
            p.get("export_konzentration", 0.5),
            p.get("import_kritische_gueter", 0.5),
            p.get("partner_konzentration", 0.5),

            p.get("chokepoint_abhaengigkeit", 0.5),
            p.get("just_in_time_anteil", 0.5),
            p.get("produktions_konzentration", 0.5),
            1 - p.get("lager_puffer", 0.5),

            p.get("auslandsverschuldung", 0.5),
            p.get("kapitalmarkt_abhaengigkeit", 0.5),
            p.get("investoren_anteil", 0.5),
            p.get("fremdwaehrungs_refinanzierung", 0.5),
        ]
        countries.append(land)
        X.append(vec)
    return countries, X

def cluster_trade_supply_financial(presets: dict):

    countries = list(presets.keys())

    # Feature-Matrix: Handel, Lieferkette, Finanzen, Tech
    X = np.array([
        [
            compute_risk_scores(presets[land])["handel"],
            compute_risk_scores(presets[land])["supply_chain"],
            compute_risk_scores(presets[land])["financial"],
            compute_risk_scores(presets[land])["tech"],
        ]
        for land in countries
    ])

    # Initiale Clusterzentren (heuristisch)
    centers = np.array([
        X.mean(axis=0) - 0.15,
        X.mean(axis=0),
        X.mean(axis=0) + 0.15,
    ])

    # 5 Iterationen (K-Means Light)
    for _ in range(5):
        # Distanzmatrix
        dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)

        # Clusterzuordnung
        labels = np.argmin(dists, axis=1)

        # Zentren aktualisieren
        for k in range(3):
            if np.any(labels == k):
                centers[k] = X[labels == k].mean(axis=0)

    return countries, labels

def cluster_tech(presets):
    import numpy as np

    countries = list(presets.keys())

    X = np.array([
        [
            compute_risk_scores(presets[land])["handel"],
            compute_risk_scores(presets[land])["supply_chain"],
            compute_risk_scores(presets[land])["financial"],
            compute_risk_scores(presets[land])["tech"],
        ]
        for land in countries
    ])

    centers = np.array([
        X.mean(axis=0) - 0.15,
        X.mean(axis=0),
        X.mean(axis=0) + 0.15,
    ])

    for _ in range(5):
        dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        labels = np.argmin(dists, axis=1)

        for k in range(3):
            if np.any(labels == k):
                centers[k] = X[labels == k].mean(axis=0)

    return countries, labels


def handels_heatmap(presets: dict):
    rows = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append([land, scores["handel"]])
    return rows


def supply_chain_heatmap(presets: dict):
    rows = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append([land, scores["supply_chain"]])
    return rows

def abhaengigkeiten_heatmap(presets: dict):
    rows = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append([
            land,
            scores["handel"],
            scores["supply_chain"],
            scores["financial"],
        ])
    return rows

def tech_heatmap(presets):
    rows = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        t = scores["tech"]

        if t < 0.33:
            color = "🟢"
        elif t < 0.66:
            color = "🟡"
        else:
            color = "🔴"

        rows.append([land, round(t, 3), color])

    return rows

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


def generate_benchmark_interpretation(scores: dict):
    """
    scores = {
        "DE": {"total":..., "macro":..., ...},
        "US": {...},
        ...
    }
    """
    text = "Benchmark-Analyse:\n\n"

    # Ranking
    ranking = sorted(scores.items(), key=lambda x: x[1]["total"])
    text += "Risikoranking (niedrig → hoch):\n"
    for i, (land, sc) in enumerate(ranking, 1):
        text += f"{i}. {land}: {sc['total']:.3f}\n"

    # Unterschiede hervorheben
    best = ranking[0][0]
    worst = ranking[-1][0]

    text += f"\nNiedrigstes Risiko: {best}\n"
    text += f"Höchstes Risiko: {worst}\n"

    # Dimensionale Analyse
    text += "\nDimensionale Unterschiede:\n"
    dims = ["macro", "geo", "governance", "finanz", "sozial"]
    for d in dims:
        sorted_dim = sorted(scores.items(), key=lambda x: x[1][d])
        text += f"- {d.capitalize()}: Bestes Land = {sorted_dim[0][0]}, Schwächstes Land = {sorted_dim[-1][0]}\n"

    return text

def interpret_handel_supply(params, scores):
    text = "### Handel & Lieferketten – Automatische Interpretation\n\n"

    text += f"- Handelsrisiko: **{scores['handel']:.3f}**\n"
    text += f"- Lieferkettenrisiko: **{scores['supply_chain']:.3f}**\n\n"

    if scores["handel"] > 0.66:
        text += "• Das Land weist eine **kritische Handelsabhängigkeit** auf.\n"
    elif scores["handel"] > 0.33:
        text += "• Die Handelsabhängigkeit ist **moderat**, aber verwundbar.\n"
    else:
        text += "• Die Handelsabhängigkeit ist **gering** und gut diversifiziert.\n"

    if scores["supply_chain"] > 0.66:
        text += "• Die Lieferketten sind **hochgradig fragil**.\n"
    elif scores["supply_chain"] > 0.33:
        text += "• Die Lieferketten sind **teilweise anfällig**.\n"
    else:
        text += "• Die Lieferketten sind **robust**.\n"

    return text

def interpret_country_full_old(name: str, params: dict, scores: dict) -> str:
    lines = []
    lines.append(f"## Länderprofil: {name}\n")

    # Gesamtbild
    lines.append(f"- Gesamtrisiko: **{scores['total']:.3f}**")
    lines.append(f"- Makro-Risiko: **{scores['macro']:.3f}**")
    lines.append(f"- Geo-Risiko: **{scores['geo']:.3f}**")
    lines.append(f"- Governance-Risiko: **{scores['governance']:.3f}**")
    lines.append(f"- Handels-Risiko: **{scores['handel']:.3f}**")
    lines.append(f"- Lieferketten-Risiko: **{scores['supply_chain']:.3f}**")
    lines.append(f"- Finanzielle Abhängigkeit: **{scores['financial']:.3f}**\n")
    lines.append("")

    # Makro
    if scores["macro"] > 0.66:
        lines.append("• Makroökonomische Lage: **kritisch** – hohe Verschuldung, FX-Risiken oder geringe Reserven.")
    elif scores["macro"] > 0.33:
        lines.append("• Makroökonomische Lage: **angespannt** – Verwundbarkeiten vorhanden, aber noch beherrschbar.")
    else:
        lines.append("• Makroökonomische Lage: **stabil** – solide Puffer und begrenzte Schockanfälligkeit.")

    # Geo
    if scores["geo"] > 0.66:
        lines.append("• Geopolitische Lage: **hohes Risiko** – starke Abhängigkeit von USD, Sanktionen oder fehlenden Alternativen.")
    elif scores["geo"] > 0.33:
        lines.append("• Geopolitische Lage: **mittleres Risiko** – gewisse Abhängigkeiten, aber mit Ausweichoptionen.")
    else:
        lines.append("• Geopolitische Lage: **relativ robust** – Diversifizierung und Alternativnetzwerke vorhanden.")

    # Governance
    if scores["governance"] > 0.66:
        lines.append("• Governance: **schwach** – Defizite bei Demokratie, Korruptionskontrolle oder Fachkräften.")
    elif scores["governance"] > 0.33:
        lines.append("• Governance: **durchwachsen** – gemischtes Bild mit Stärken und Schwächen.")
    else:
        lines.append("• Governance: **stark** – gute Institutionen, Innovationskraft und Fachkräftebasis.")

    # Handel 
    if scores["handel"] > 0.66:
        lines.append("• Handel: **hohe Abhängigkeit** – starke Konzentration bei Exporten, Importen oder Partnern.")
    elif scores["handel"] > 0.33:
        lines.append("• Handel: **moderate Abhängigkeit** – Diversifizierung ausbaufähig.")
    else:
        lines.append("• Handel: **gut diversifiziert** – begrenzte strukturelle Abhängigkeiten.")

    # Lieferketten
    if scores["supply_chain"] > 0.66:
        lines.append("• Lieferketten: **fragil** – hohe Abhängigkeit von Chokepoints, Just-in-Time und konzentrierter Produktion.")
    elif scores["supply_chain"] > 0.33:
        lines.append("• Lieferketten: **teilweise anfällig** – gewisse Risiken, aber mit Puffer- und Ausweichmöglichkeiten.")
    else:
        lines.append("• Lieferketten: **robust** – Puffer, Diversifizierung und resiliente Logistikstrukturen.")

    # Finanzen
    if scores["financial"] > 0.66:
        lines.append("• Finanzielle Abhängigkeit: **hoch** – starke Kapitalmarktbindung oder FX-Refinanzierung.")
    elif scores["financial"] > 0.33:
        lines.append("• Finanzielle Abhängigkeit: **moderat**.")
    else:
        lines.append("• Finanzielle Abhängigkeit: **gering** – stabile Finanzierungsbasis.")
    
    return "\n".join(lines)


def interpret_cluster(label: int) -> str:
    if label == 0:
        return (
            "Cluster 0: **Hohe Abhängigkeiten** – fragil, konzentriert, störungsanfällig.\n"
            "- Hohe Handels- und Lieferkettenrisiken\n"
            "- Hohe finanzielle Abhängigkeit\n"
            "- Starkes Tech-Risiko"
        )
    elif label == 1:
        return (
            "Cluster 1: **Mittlere Abhängigkeiten** – teilweise diversifiziert.\n"
            "- Gemischtes Risikoprofil\n"
            "- Einzelne Schwachstellen\n"
            "- Moderate Tech-Abhängigkeit"
        )
    else:
        return (
            "Cluster 2: **Niedrige Abhängigkeiten** – resilient und diversifiziert.\n"
            "- Robuste Lieferketten\n"
            "- Geringe finanzielle Abhängigkeit\n"
            "- Geringes Tech-Risiko"
        )

def interpret_scores(scores: dict) -> str:
    lines = []
    total = scores["total"]

    # Gesamtbild
    if total > 0.75:
        lines.append("Das Gesamtrisiko liegt im **kritischen Bereich**. Mehrere strukturelle Verwundbarkeiten überlagern sich.")
    elif total > 0.55:
        lines.append("Das Gesamtrisiko ist **erhöht**. Einzelne Risikofaktoren dominieren das Profil.")
    else:
        lines.append("Das Gesamtrisiko ist **moderat bis stabil**. Keine dominanten systemischen Schwächen.")

    # Makro
    if scores["macro"] > 0.66:
        lines.append("• **Makroökonomisch kritisch**: Verschuldung, FX‑Risiken oder geringe Reserven belasten die Stabilität.")
    elif scores["macro"] > 0.33:
        lines.append("• **Makroökonomisch angespannt**: Einige Verwundbarkeiten sind sichtbar.")
    else:
        lines.append("• **Makroökonomisch solide**: Puffer und Stabilität vorhanden.")

    # Geo
    if scores["geo"] > 0.66:
        lines.append("• **Geopolitisch hoch riskant**: Starke Abhängigkeiten oder Sanktionsrisiken.")
    elif scores["geo"] > 0.33:
        lines.append("• **Geopolitisch moderat riskant**: Teilweise Abhängigkeiten bestehen.")
    else:
        lines.append("• **Geopolitisch robust**: Diversifizierte Position.")

    # Governance
    if scores["governance"] > 0.66:
        lines.append("• **Governance schwach**: Institutionelle Risiken, Korruption oder geringe Innovationskraft.")
    elif scores["governance"] > 0.33:
        lines.append("• **Governance durchwachsen**: Reformbedarf vorhanden.")
    else:
        lines.append("• **Governance stark**: Gute Institutionen und Innovationsfähigkeit.")

    # Handel
    if scores["handel"] > 0.66:
        lines.append("• **Handelsabhängigkeit hoch**: Konzentration auf wenige Partner oder kritische Güter.")
    elif scores["handel"] > 0.33:
        lines.append("• **Handelsrisiko moderat**.")
    else:
        lines.append("• **Handel gut diversifiziert**.")

    # Lieferketten
    if scores["supply_chain"] > 0.66:
        lines.append("• **Lieferketten fragil**: Chokepoints oder geringe Puffer.")
    elif scores["supply_chain"] > 0.33:
        lines.append("• **Lieferketten teilweise anfällig**.")
    else:
        lines.append("• **Lieferketten robust**.")

    # Finanzielle Abhängigkeit
    if scores["financial"] > 0.66:
        lines.append("• **Finanzielle Abhängigkeit hoch**: Kapitalmarkt‑ oder FX‑Refinanzierungsrisiken.")
    elif scores["financial"] > 0.33:
        lines.append("• **Finanzielle Abhängigkeit moderat**.")
    else:
        lines.append("• **Finanzielle Abhängigkeit gering**.")

    # Tech-Abhängigkeit
    if scores["tech"] > 0.66:
        lines.append("• **Technologische Abhängigkeit kritisch**: Hohe Importabhängigkeit bei Halbleitern, Software oder Schlüsseltechnologien.")
    elif scores["tech"] > 0.33:
        lines.append("• **Technologische Abhängigkeit moderat**: Teilweise Abhängigkeit von externen Hightech-Komponenten.")
    else:
        lines.append("• **Technologische Abhängigkeit gering**: Gute technologische Eigenständigkeit.")


    return "\n".join(lines)


def interpret_country(name: str, params: dict) -> str:
    scores = compute_risk_scores(params)

    lines = []
    lines.append(f"## Länderprofil: {name}\n")

    # Gesamtbild
    lines.append(f"- **Gesamtrisiko:** {scores['total']:.3f}")
    lines.append(f"- **Makro:** {scores['macro']:.3f}")
    lines.append(f"- **Geo:** {scores['geo']:.3f}")
    lines.append(f"- **Governance:** {scores['governance']:.3f}")
    lines.append(f"- **Handel:** {scores['handel']:.3f}")
    lines.append(f"- **Lieferketten:** {scores['supply_chain']:.3f}")
    lines.append(f"- **Finanzen:** {scores['financial']:.3f}")
    lines.append(f"- **Technologie:** {scores['tech']:.3f}\n")

    # Makro
    if scores["macro"] > 0.66:
        lines.append("• **Makroökonomische Lage: kritisch** – hohe Verschuldung, FX-Risiken oder geringe Reserven.")
    elif scores["macro"] > 0.33:
        lines.append("• **Makroökonomische Lage: angespannt** – Verwundbarkeiten vorhanden, aber beherrschbar.")
    else:
        lines.append("• **Makroökonomische Lage: stabil** – solide Puffer und geringe Schockanfälligkeit.")

    # Geo
    if scores["geo"] > 0.66:
        lines.append("• **Geopolitische Lage: hohes Risiko** – starke USD-Abhängigkeit, Sanktionen oder fehlende Alternativen.")
    elif scores["geo"] > 0.33:
        lines.append("• **Geopolitische Lage: mittleres Risiko** – gewisse Abhängigkeiten, aber Ausweichoptionen vorhanden.")
    else:
        lines.append("• **Geopolitische Lage: robust** – Diversifizierung und Alternativnetzwerke vorhanden.")

    # Governance
    if scores["governance"] > 0.66:
        lines.append("• **Governance: schwach** – Defizite bei Demokratie, Korruption oder Fachkräften.")
    elif scores["governance"] > 0.33:
        lines.append("• **Governance: durchwachsen** – gemischtes Bild mit Stärken und Schwächen.")
    else:
        lines.append("• **Governance: stark** – gute Institutionen, Innovationskraft und Fachkräftebasis.")

    # Handel
    if scores["handel"] > 0.66:
        lines.append("• **Handel: hohe Abhängigkeit** – starke Konzentration bei Exporten, Importen oder Partnern.")
    elif scores["handel"] > 0.33:
        lines.append("• **Handel: moderat abhängig** – Diversifizierung ausbaufähig.")
    else:
        lines.append("• **Handel: gut diversifiziert** – geringe strukturelle Abhängigkeiten.")

    # Lieferketten
    if scores["supply_chain"] > 0.66:
        lines.append("• **Lieferketten: fragil** – hohe Abhängigkeit von Chokepoints, JIT oder konzentrierter Produktion.")
    elif scores["supply_chain"] > 0.33:
        lines.append("• **Lieferketten: teilweise anfällig** – gewisse Risiken, aber Puffer vorhanden.")
    else:
        lines.append("• **Lieferketten: robust** – gute Diversifizierung und resiliente Logistik.")

    # Finanzen
    if scores["financial"] > 0.66:
        lines.append("• **Finanzielle Abhängigkeit: hoch** – starke Kapitalmarktbindung oder FX-Refinanzierung.")
    elif scores["financial"] > 0.33:
        lines.append("• **Finanzielle Abhängigkeit: moderat**.")
    else:
        lines.append("• **Finanzielle Abhängigkeit: gering** – stabile Finanzierungsbasis.")

    # Technologie
    if scores["tech"] > 0.66:
        lines.append("• **Technologische Abhängigkeit: hoch** – starke Importabhängigkeit bei Halbleitern, Software oder IP.")
    elif scores["tech"] > 0.33:
        lines.append("• **Technologische Abhängigkeit: moderat** – gewisse Abhängigkeiten, aber Alternativen vorhanden.")
    else:
        lines.append("• **Technologische Abhängigkeit: gering** – robuste technologische Basis und Diversifizierung.")

    return "\n".join(lines)

def interpret_dashboard(params: dict, scores: dict) -> str:
    lines = []
    lines.append("## Interpretation des Dashboards\n")

    # Gesamtampel
    if scores["total"] > 0.75:
        lines.append("Das Gesamtrisiko befindet sich im **kritischen Bereich**. Mehrere Risikodimensionen verstärken sich gegenseitig.")
    elif scores["total"] > 0.55:
        lines.append("Das Gesamtrisiko ist **erhöht**, jedoch nicht akut kritisch.")
    else:
        lines.append("Das Gesamtrisiko ist **moderat** und zeigt keine unmittelbaren systemischen Spannungen.")

    # Systemrisiko-Radar
    lines.append("\n### Systemrisiko-Radar")
    lines.append("Das Radar zeigt die strukturelle Balance zwischen Makro, Geo, Governance und Abhängigkeiten.")

    # Frühwarnindikatoren
    lines.append("\n### Frühwarnindikatoren")
    lines.append(build_early_warning_dashboard(params, scores))

    # Handelsrisiken
    if scores["handel"] > 0.66:
        lines.append("\n### Handelsrisiko")
        lines.append("Hohe Handelsabhängigkeit – Diversifizierung empfohlen.")
    elif scores["handel"] > 0.33:
        lines.append("\n### Handelsrisiko")
        lines.append("Moderate Handelsrisiken – Monitoring sinnvoll.")
    else:
        lines.append("\n### Handelsrisiko")
        lines.append("Handel gut diversifiziert.")

    # Lieferketten
    if scores["supply_chain"] > 0.66:
        lines.append("\n### Lieferketten")
        lines.append("Lieferketten sind fragil – Chokepoints und geringe Puffer.")
    elif scores["supply_chain"] > 0.33:
        lines.append("\n### Lieferketten")
        lines.append("Teilweise Verwundbarkeit – Puffer erhöhen.")
    else:
        lines.append("\n### Lieferketten")
        lines.append("Lieferketten robust.")

    # Finanzielle Abhängigkeit
    if scores["financial"] > 0.66:
        lines.append("\n### Finanzielle Abhängigkeit")
        lines.append("Hohe externe Abhängigkeit – Kapitalmarkt‑ oder FX‑Risiken.")
    elif scores["financial"] > 0.33:
        lines.append("\n### Finanzielle Abhängigkeit")
        lines.append("Moderate externe Abhängigkeit.")
    else:
        lines.append("\n### Finanzielle Abhängigkeit")
        lines.append("Geringe externe Abhängigkeit.")

    
    lines.append("\n### Technologische Abhängigkeit")
    if scores["tech"] > 0.66:
        lines.append("Hohe technologische Abhängigkeit – Risiken bei Halbleitern, Software oder Cloud-Infrastruktur.")
    elif scores["tech"] > 0.33:
        lines.append("Moderate technologische Abhängigkeit – Monitoring sinnvoll.")
    else:
        lines.append("Geringe technologische Abhängigkeit – robuste technologische Basis.")

    return "\n".join(lines)

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
        with gr.Tab("Heatmaps"):
            # --- Standard-Risiko-Heatmap ---
            gr.Markdown("### 1) Heatmaps der Risikotreiber")
            # Standard-Heatmap
            gr.Markdown("### 1) Standard-Risiko-Heatmap")

            heat_button = gr.Button("Heatmap erzeugen")
            heat_output = gr.Dataframe(
                headers=[
                    "Land", "Makro", "Makro-Farbe",
                    "Geo", "Geo-Farbe",
                    "Gov", "Gov-Farbe",
                    "Total", "Total-Farbe",
                ],
                wrap=True,
                label="Standard-Risiko-Heatmap",

            )

            heat_button.click(ui_heatmap,None, heat_output)
             
            with gr.Accordion("Interpretation", open=False):
                gr.Markdown(f"```\n{heatmap_text}\n```")


            # --- Tech-Risiko-Heatmap ---
            gr.Markdown("### 2) Tech-Risiko-Heatmap")

            tech_button = gr.Button("Tech-Heatmap aktualisieren")

            tech_output = gr.Dataframe(
                headers=["Land", "Tech-Risiko", "Ampel"],
                wrap=True,
                label="Tech-Risiko-Heatmap", 
            )

            tech_button.click(lambda: tech_heatmap(presets), None, tech_output)


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
        # TAB 6 — DASHBOARD
        # ----------------------------------------------------
        with gr.Tab("Dashboard"):

            gr.Markdown("### Dashboard – Gesamtrisiko & Radar")

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
                label="Risiko-Heatmap",
            )

            dash_handel_radar = gr.Plot(label="Handels-Radar")
            dash_handel_heatmap = gr.Dataframe(
                headers=["Land", "Handels-Risiko"],
                wrap=True,
                label="Handels-Heatmap",
            )

            # Systemrisiko-Radar (optional separat)
            sys_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land (Systemrisiko-Radar)",
                value=list(presets.keys())[0],
            )
            sys_radar = gr.Plot(label="Systemrisiko-Radar")

            def ui_system_radar(country):
                params = presets[country]
                return plot_systemrisiko_radar(params)

            sys_country.change(
                fn=ui_system_radar,
                inputs=[sys_country],
                outputs=[sys_radar],
            )

            # Interpretation

            dash_interpret = gr.Markdown()

            with gr.Accordion("Interpretation des Dashboards", open=False):
                gr.Markdown(f"```\n{dashboard_text}\n```")
                dash_interpret


            # Dashboard-Funktion
            def ui_dashboard(country):
                params = presets[country]
                scores = compute_risk_scores(params)
                default_scores = compute_risk_scores(default_params)

                # Ampel
                cat, color = risk_category(scores["total"])
                ampel = f"### Risiko-Ampel: **{scores['total']:.3f} ({cat})**"

                # Plots
                fig_radar = plot_radar(scores)
                fig_res = plot_resilience_radar(scores)
                fig_delta = plot_delta_radar(default_scores, scores)

                # Frühwarnsystem
                warn = build_early_warning_dashboard(params, scores)
                warn_md = "### Frühwarnindikatoren\n" + warn.replace("-", "•")

                # Mini-Prognose
                values = forecast(params, years=10)
                fig_forecast = plot_forecast(values)

                # Risiko-Heatmap (bestehende Logik)
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

                # Handels-Radar
                fig_handel = plot_handel_radar(params)

                # Handels-Heatmap
                handel_rows = handels_heatmap(presets)
                # Dynamische Interpretation
                interpretation = interpret_dashboard(params, scores)

                return (
                    ampel,
                    fig_radar,
                    fig_res,
                    fig_delta,
                    warn_md,
                    fig_forecast,
                    rows,
                    fig_handel,
                    handel_rows,
                    interpretation,
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
                    dash_handel_radar,
                    dash_handel_heatmap,
                    dash_interpret,
                ],
            )

        # ----------------------------------------------------
        # TAB 7 — BENCHMARKING
        # ----------------------------------------------------
        with gr.Tab("Benchmarking"):

            gr.Markdown("### Länder-Benchmarking: Vergleich mehrerer Länder")

            # Auswahl
            bench_main = gr.Dropdown(
                choices=list(presets.keys()),
                label="Hauptland",
                value=list(presets.keys())[0],
            )

            bench_compare = gr.Dropdown(
                choices=list(presets.keys()),
                label="Vergleichsländer",
                multiselect=True,
                value=["US", "CN"],
            )

            bench_button = gr.Button("Benchmark starten")

            # Outputs
            bench_multi_radar = gr.Plot()
            bench_heatmap = gr.Dataframe(
                headers=["Land", "Makro", "Geo", "Governance", "Finanz", "Sozial", "Total"],
                wrap=True,
            )
            bench_ranking = gr.Dataframe(
                headers=["Rang", "Land", "Risiko"],
                wrap=True,
            )
            bench_interpret = gr.Textbox(label="Automatische Benchmark-Interpretation", lines=12)

            # Benchmark-Funktion
            def ui_benchmark(main, compare):
                if main not in presets:
                    return None, None, None, "Ungültiges Hauptland."

                countries = [main] + compare

                # Risiko-Scores berechnen
                score_dict = {}
                for c in countries:
                    params = presets[c]
                    score_dict[c] = compute_risk_scores(params)

                # Multi-Radar
                fig = plot_multi_radar(score_dict)

                # Mini-Heatmap
                heat_rows = []
                for c, sc in score_dict.items():
                    heat_rows.append([
                        c,
                        sc["macro"],
                        sc["geo"],
                        sc["governance"],
                        sc["finanz"],
                        sc["sozial"],
                        sc["total"],
                    ])

                # Ranking
                ranking = sorted(score_dict.items(), key=lambda x: x[1]["total"])
                rank_rows = []
                for i, (land, sc) in enumerate(ranking, 1):
                    rank_rows.append([i, land, sc["total"]])

                # Automatische Interpretation
                interpretation = generate_benchmark_interpretation(score_dict)

                return fig, heat_rows, rank_rows, interpretation

            bench_button.click(
                fn=ui_benchmark,
                inputs=[bench_main, bench_compare],
                outputs=[bench_multi_radar, bench_heatmap, bench_ranking, bench_interpret],
            )

            # Externe Interpretation
            with gr.Accordion("Interpretation des Benchmarkings", open=False):
                gr.Markdown(f"```\n{benchmarking_text}\n```")

        
        
        # ----------------------------------------------------
        # TAB 8 — HANDEL & LIEFERKETTEN
        # ----------------------------------------------------
        with gr.Tab("Handel & Lieferketten"):
            gr.Markdown("### Analyse: Handelsabhängigkeit & Lieferkettenrisiko")

            hls_country = gr.Dropdown(
                choices=list(presets.keys()),
                label="Land",
                value=list(presets.keys())[0],
            )

            hls_handel_radar = gr.Plot(label="Handels-Radar")
            hls_supply_radar = gr.Plot(label="Lieferketten-Radar")
            hls_abhaengigkeiten_radar = gr.Plot(label="Abhängigkeiten-Radar")

            hls_handel_heatmap = gr.Dataframe(
                headers=["Land", "Handels-Risiko"],
                wrap=True,
                label="Handels-Heatmap",
            )

            hls_abhaengigkeiten_heatmap = gr.Dataframe(
                headers=["Land", "Handel", "Lieferkette", "Finanzen"],
                wrap=True,
                label="Abhängigkeiten-Heatmap",
            )

            hls_supply_heatmap = gr.Dataframe(
                headers=["Land", "Lieferketten-Risiko"],
                wrap=True,
                label="Lieferketten-Heatmap",
            )

            hls_interpret = gr.Markdown()

            def ui_handel_supply(country):
                params = presets[country]
                scores = compute_risk_scores(params)

                fig_handel = plot_handel_radar(params)
                fig_supply = plot_supply_chain_radar(params)
                fig_abhaeng = plot_abhaengigkeiten_radar(params)

                heat_handel = handels_heatmap(presets)
                heat_supply = supply_chain_heatmap(presets)
                heat_abhaeng = abhaengigkeiten_heatmap(presets)


                interpretation = interpret_handel_supply(params, scores)
                warnings = build_trade_supply_early_warning(params, scores)

                return (
                    fig_handel,
                    fig_supply,
                    fig_abhaeng,
                    heat_handel,
                    heat_supply,
                    heat_abhaeng,
                    interpretation + "\n\n" + warnings,
                )


            hls_country.change(
                fn=ui_handel_supply,
                inputs=[hls_country],
                outputs=[
                    hls_handel_radar,
                    hls_supply_radar,
                    hls_abhaengigkeiten_radar,
                    hls_handel_heatmap,
                    hls_supply_heatmap,
                    hls_abhaengigkeiten_heatmap,   # <-- NEU
                    hls_interpret,
                ],
              
            ) 

            with gr.Accordion("Interpretation Handel & Lieferketten", open=False):
                gr.Markdown(f"```\n{handel_lieferketten_text}\n```")
        

        # ----------------------------------------------------
        # TAB 9 — CLUSTERANALYSE
        # ----------------------------------------------------
        with gr.Tab("Clusteranalyse"):
            gr.Markdown("## Clusteranalyse: Handel + Lieferketten + Finanzen + Tech")

            cluster_button = gr.Button("Cluster berechnen")
            cluster_output = gr.Dataframe(
                headers=["Land", "Cluster", "Interpretation"],
                wrap=True,
                label="Cluster-Ergebnisse",
            )

            def ui_cluster():
                countries, labels = cluster_trade_supply_financial(presets)
                return [
                    [land, int(label), interpret_cluster(int(label))]
                    for land, label in zip(countries, labels)
                ]

            cluster_button.click(ui_cluster, None, cluster_output)

        # ----------------------------------------------------
        # TAB Optional
        # ----------------------------------------------------
        with gr.Tab("Länderprofil"):
            country_select = gr.Dropdown(list(presets.keys()), label="Land auswählen")
            interp_button = gr.Button("Profil erzeugen")
            interp_output = gr.Markdown()

            interp_button.click(
                lambda land: interpret_country(land, presets[land]),
                country_select,
                interp_output,
            )

        # ----------------------------------------------------
        # TAB 10 — METHODIK
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
