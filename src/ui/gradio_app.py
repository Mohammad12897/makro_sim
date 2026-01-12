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
import seaborn as sns


# ------------------------------------------------------------
# 1. Datenbasis laden
# ------------------------------------------------------------

#with open("slider_presets.json", "r", encoding="utf-8") as f:
#    presets = json.load(f)

# ------------------------------------------------------------
# 2. Risiko- und Statusfunktionen (werden bei dir schon existieren)
# ------------------------------------------------------------

# Annahme: existiert in deinem Projekt
# def compute_risk_scores(params: dict) -> dict: ...

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

def load_lexikon():
    lexikon_path = ROOT.parent / "docs" / "risk_methodology.md"
    print (lexikon_path)
    if lexikon_path.exists():
        return lexikon_path.read_text(encoding="utf-8")
    return "Lexikon nicht gefunden."

try:
    lexikon_erweitert_markdown = load_lexikon()
except Exception:
    lexikon_erweitert_markdown = "Lexikon konnte nicht geladen werden."


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
technologische_abhaengigkeit_text = load_textfile(ROOT.parent / "docs" / "interpretation_technologische_abhaengigkeit.txt")

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
    handel = scores.get("handel", 0.0)
    supply = scores.get("supply_chain", 0.0)
    financial = scores.get("financial", 0.0)
    tech = scores.get("tech", 0.0)
    energie = scores.get("energie", 0.0)

    # --- Gesamtwarnung ---
    if total > 0.75:
        warnings.append("⚠️ **Gesamtrisiko kritisch hoch** – sofortige Maßnahmen erforderlich.")
    elif total > 0.55:
        warnings.append("⚠️ **Gesamtrisiko erhöht** – erhöhte Wachsamkeit empfohlen.")

    # --- Makro ---
    if macro > 0.7:
        warnings.append("• Makroökonomische Instabilität (Inflation, Wachstum, Arbeitsmarkt).")

    # --- Geo ---
    if geo > 0.7:
        warnings.append("• Hohe geopolitische Risiken (Konflikte, Sanktionen, Rivalitäten).")

    # --- Governance ---
    if gov > 0.7:
        warnings.append("• Schwache Governance-Strukturen und politische Unsicherheit.")

    # --- Handel ---
    if handel > 0.7:
        warnings.append("• Kritische Handelsabhängigkeit von wenigen Partnern.")

    # --- Lieferkette ---
    if supply > 0.7:
        warnings.append("• Hohe Verwundbarkeit der Lieferketten (Single-Sourcing, geringe Diversifikation).")

    # --- Finanzen ---
    if financial > 0.7:
        warnings.append("• Finanzielle Instabilität (Kapitalflüsse, Verschuldung, Zinsrisiken).")

    # --- Tech ---
    if tech > 0.7:
        warnings.append("• Kritische technologische Abhängigkeit (Halbleiter, Cloud, IP).")

    # --- Energie ---
    if energie > 0.7:
        warnings.append("• Kritische Energieabhängigkeit – hohe Importabhängigkeit und Schockrisiken.")

    if not warnings:
        return "Keine akuten Frühwarnsignale – Risiko derzeit stabil."

    return "\n".join(warnings)

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

def tech_early_warning(params: dict) -> str:
    warnings = []

    if params["halbleiter_abhaengigkeit"] > 0.75:
        warnings.append("⚠️ Hohe Halbleiter-Abhängigkeit – Risiko bei globalen Chip-Schocks.")

    if params["software_cloud_abhaengigkeit"] > 0.75:
        warnings.append("⚠️ Starke Cloud-Abhängigkeit – Risiko bei US/EU-Regulierungen.")

    if params["ip_lizenzen_abhaengigkeit"] > 0.75:
        warnings.append("⚠️ Hohe IP-Lizenzabhängigkeit – Gefahr durch Lizenzentzug.")

    if params["schluesseltechnologie_importe"] > 0.75:
        warnings.append("⚠️ Kritische Abhängigkeit von Schlüsseltechnologien – Lieferstopps möglich.")

    if not warnings:
        return "Keine kritischen Tech-Risiken erkannt."

    return "\n".join(warnings)

def tech_storyline(name: str, params: dict) -> str:
    h = params["halbleiter_abhaengigkeit"]
    s = params["software_cloud_abhaengigkeit"]
    ip = params["ip_lizenzen_abhaengigkeit"]
    k = params["schluesseltechnologie_importe"]

    lines = [f"## Tech-Storyline: {name}\n"]

    if h > 0.75:
        lines.append("• Das Land ist stark von globalen Halbleitern abhängig – ein externer Schock hätte große Auswirkungen.")
    elif h > 0.5:
        lines.append("• Moderate Halbleiter-Abhängigkeit – Risiken bestehen, aber sind kontrollierbar.")
    else:
        lines.append("• Geringe Halbleiter-Abhängigkeit – robuste lokale Alternativen.")

    if s > 0.75:
        lines.append("• Hohe Cloud-Abhängigkeit – mögliche Verwundbarkeit gegenüber geopolitischen Spannungen.")
    elif s > 0.5:
        lines.append("• Moderate Cloud-Abhängigkeit – Diversifizierung wäre sinnvoll.")
    else:
        lines.append("• Geringe Cloud-Abhängigkeit – gute digitale Souveränität.")

    if ip > 0.75:
        lines.append("• Kritische Abhängigkeit von IP-Lizenzen – Gefahr durch Lizenzentzug.")
    elif ip > 0.5:
        lines.append("• Moderate IP-Abhängigkeit – Risiken bestehen, aber sind beherrschbar.")
    else:
        lines.append("• Geringe IP-Abhängigkeit – stabile Innovationsbasis.")

    if k > 0.75:
        lines.append("• Hohe Abhängigkeit von Schlüsseltechnologie-Importen – Lieferstopps wären problematisch.")
    elif k > 0.5:
        lines.append("• Moderate Abhängigkeit von Schlüsseltechnologien – Diversifizierung empfehlenswert.")
    else:
        lines.append("• Geringe Abhängigkeit von Schlüsseltechnologien – gute technologische Resilienz.")

    return "\n".join(lines)


# ============================================================
# RADAR-FUNKTIONEN
# ============================================================

def tech_delta_radar(old_params: dict, new_params: dict):
    import matplotlib.pyplot as plt
    import numpy as np

    labels = ["Halbleiter", "Software/Cloud", "IP/Lizenzen", "Schlüsseltechnologien"]

    old_vals = [
        old_params["halbleiter_abhaengigkeit"],
        old_params["software_cloud_abhaengigkeit"],
        old_params["ip_lizenzen_abhaengigkeit"],
        old_params["schluesseltechnologie_importe"],
    ]

    new_vals = [
        new_params["halbleiter_abhaengigkeit"],
        new_params["software_cloud_abhaengigkeit"],
        new_params["ip_lizenzen_abhaengigkeit"],
        new_params["schluesseltechnologie_importe"],
    ]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    old_vals = np.concatenate((old_vals, [old_vals[0]]))
    new_vals = np.concatenate((new_vals, [new_vals[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    ax.plot(angles, old_vals, "o--", label="Vorher", linewidth=1.5)
    ax.plot(angles, new_vals, "o-", label="Nachher", linewidth=2)

    ax.fill(angles, new_vals, alpha=0.2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right")

    return fig

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


def plot_delta_radar(country):
    p = presets[country]

    # Prüfen, ob t0/t1 existieren
    if "t0" not in p or "t1" not in p:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine t0/t1 Daten vorhanden", ha="center", fontsize=14)
        ax.axis("off")
        return fig

    p0 = p["t0"]
    p1 = p["t1"]

    s0 = compute_risk_scores(p0)
    s1 = compute_risk_scores(p1)

    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie"
    ]

    dims = ["macro","geo","governance","handel",
            "supply_chain","financial","tech","energie"]

    v0 = [s0[d] for d in dims]
    v1 = [s1[d] for d in dims]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    ax.plot(angles, v0 + [v0[0]], label="t0", linewidth=2)
    ax.plot(angles, v1 + [v1[0]], label="t1", linewidth=2)

    ax.fill(angles, v0 + [v0[0]], alpha=0.15)
    ax.fill(angles, v1 + [v1[0]], alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend()

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

def risk_radar(scores: Dict[str, float]):
    labels = ["Makro", "Geo", "Governance", "Handel", "Lieferkette", "Finanzen", "Tech", "Energie"]
    values = [
        scores["macro"],
        scores["geo"],
        scores["governance"],
        scores["handel"],
        scores["supply_chain"],
        scores["financial"],
        scores["tech"],
        scores["energie"],   # NEU
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)

    return fig

def multi_radar(presets):
    labels = ["Makro", "Geo", "Governance", "Handel", "Lieferkette", "Finanzen", "Tech", "Energie"]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        values = [
            scores["macro"],
            scores["geo"],
            scores["governance"],
            scores["handel"],
            scores["supply_chain"],
            scores["financial"],
            scores["tech"],
            scores["energie"],   # NEU
        ]
        values = np.concatenate((values, [values[0]]))

        ax.plot(angles, values, linewidth=1.5, label=land)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

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
            compute_risk_scores(presets[land])["energie"],   # NEU
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
            compute_risk_scores(presets[land])["energie"],   # NEU
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

def tech_radar(params: dict):
    labels = [
        "Halbleiter",
        "Software/Cloud",
        "IP/Lizenzen",
        "Schlüsseltechnologien"
    ]

    values = [
        params["halbleiter_abhaengigkeit"],
        params["software_cloud_abhaengigkeit"],
        params["ip_lizenzen_abhaengigkeit"],
        params["schluesseltechnologie_importe"]
    ]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    values = np.concatenate((values, [values[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)

    return fig

def multi_radar(presets):
    labels = ["Makro", "Geo", "Gov", "Handel", "Lieferkette", "Finanzen", "Tech", "Energie"]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        values = [
            scores["macro"],
            scores["geo"],
            scores["governance"],
            scores["handel"],
            scores["supply_chain"],
            scores["financial"],
            scores["tech"],
            scores["Energie"],
        ]
        values = np.concatenate((values, [values[0]]))
        ax.plot(angles, values, linewidth=1.5, label=land)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return fig

def tech_delta_radar(old_params: dict, new_params: dict):
    labels = ["Halbleiter", "Software/Cloud", "IP/Lizenzen", "Schlüsseltechnologien"]

    old_vals = [
        old_params["halbleiter_abhaengigkeit"],
        old_params["software_cloud_abhaengigkeit"],
        old_params["ip_lizenzen_abhaengigkeit"],
        old_params["schluesseltechnologie_importe"],
    ]

    new_vals = [
        new_params["halbleiter_abhaengigkeit"],
        new_params["software_cloud_abhaengigkeit"],
        new_params["ip_lizenzen_abhaengigkeit"],
        new_params["schluesseltechnologie_importe"],
    ]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    old_vals = np.concatenate((old_vals, [old_vals[0]]))
    new_vals = np.concatenate((new_vals, [new_vals[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    ax.plot(angles, old_vals, "o--", label="Vorher", linewidth=1.5)
    ax.plot(angles, new_vals, "o-", label="Nachher", linewidth=2)

    ax.fill(angles, new_vals, alpha=0.2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right")

    return fig

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



# ------------------------------------------------------------
# 3. Radar-Plots
# ------------------------------------------------------------
def plot_status_radar(scores: dict):
    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]
    values = [
        scores["macro"],
        scores["geo"],
        scores["governance"],
        scores["finanz"],
        scores["sozial"],
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)

    return fig

def plot_risk_radar(scores: dict):
    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie"
    ]

    values = [
        scores["macro"],
        scores["geo"],
        scores["governance"],
        scores["handel"],
        scores["supply_chain"],
        scores["financial"],
        scores["tech"],
        scores["energie"],
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    values = np.concatenate((values, [values[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)

    return fig

def plot_multi_risk_radar(presets: dict):
    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie"
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    for land, params in presets.items():
        scores = compute_risk_scores(params)

        values = [
            scores["macro"],
            scores["geo"],
            scores["governance"],
            scores["handel"],
            scores["supply_chain"],
            scores["financial"],
            scores["tech"],
            scores["energie"],
        ]
        values = np.concatenate((values, [values[0]]))

        ax.plot(angles, values, linewidth=1.5, label=land)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return fig

# ------------------------------------------------------------
# 4. Clusteranalyse + Hilfsfunktionen
# ------------------------------------------------------------

def cluster_risk_dimensions(presets: dict):
    countries = list(presets.keys())

    X = np.array([
        [
            compute_risk_scores(presets[land])["handel"],
            compute_risk_scores(presets[land])["supply_chain"],
            compute_risk_scores(presets[land])["financial"],
            compute_risk_scores(presets[land])["tech"],
            compute_risk_scores(presets[land])["energie"],
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


def interpret_cluster(cluster_id: int) -> str:
    if cluster_id == 0:
        return (
            "Niedrige Risiken: gut diversifizierter Handel, stabile Lieferketten, "
            "solide Finanzen, geringe Tech- und Energieabhängigkeit."
        )
    elif cluster_id == 1:
        return (
            "Mittlere Risiken: einige Abhängigkeiten in Handel, Lieferketten oder Tech; "
            "moderate Energieverwundbarkeit."
        )
    elif cluster_id == 2:
        return (
            "Hohe Risiken: starke Abhängigkeiten in Handel, Lieferketten, Tech oder Energie; "
            "anfällig für externe Schocks."
        )
    return "Unbekannt"


def plot_cluster_heatmap(presets: dict):
    countries = list(presets.keys())

    data = [
        [
            compute_risk_scores(presets[land])["handel"],
            compute_risk_scores(presets[land])["supply_chain"],
            compute_risk_scores(presets[land])["financial"],
            compute_risk_scores(presets[land])["tech"],
            compute_risk_scores(presets[land])["energie"],
        ]
        for land in countries
    ]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        data,
        annot=True,
        cmap="Reds",
        xticklabels=["Handel", "Lieferkette", "Finanzen", "Tech", "Energie"],
        yticklabels=countries,
        ax=ax
    )
    ax.set_title("Cluster-Heatmap: Risiko-Dimensionen")
    return fig


def plot_cluster_radar(presets: dict):
    countries, labels = cluster_risk_dimensions(presets)

    dims = ["handel", "supply_chain", "financial", "tech", "energie"]
    labels_radar = ["Handel", "Lieferkette", "Finanzen", "Tech", "Energie"]

    cluster_means = {}
    for c in [0, 1, 2]:
        cluster_vals = [
            [compute_risk_scores(presets[land])[d] for d in dims]
            for land, lab in zip(countries, labels)
            if lab == c
        ]
        if cluster_vals:
            cluster_means[c] = np.mean(cluster_vals, axis=0)
        else:
            cluster_means[c] = np.zeros(len(dims))

    angles = np.linspace(0, 2*np.pi, len(labels_radar), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    for c in [0, 1, 2]:
        vals = np.concatenate((cluster_means[c], [cluster_means[c][0]]))
        ax.plot(angles, vals, label=f"Cluster {c}", linewidth=2)
        ax.fill(angles, vals, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels_radar)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return fig

def plot_compare_radar(country_a, country_b):
    scores_a = compute_risk_scores(presets[country_a])
    scores_b = compute_risk_scores(presets[country_b])

    labels = ["Makro", "Geo", "Governance", "Handel", "Lieferkette", "Finanzen", "Tech", "Energie"]

    values_a = [scores_a[k] for k in ["macro","geo","governance","handel","supply_chain","financial","tech","energie"]]
    values_b = [scores_b[k] for k in ["macro","geo","governance","handel","supply_chain","financial","tech","energie"]]

    # Radar-Plot erstellen
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    ax.plot(angles, values_a + [values_a[0]], label=country_a, linewidth=2)
    ax.plot(angles, values_b + [values_b[0]], label=country_b, linewidth=2)

    ax.fill(angles, values_a + [values_a[0]], alpha=0.15)
    ax.fill(angles, values_b + [values_b[0]], alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend()

    return fig

def cluster_storyline(cluster_id: int) -> str:
    if cluster_id == 0:
        return (
            "Cluster 0: Länder mit niedrigen Risiken – "
            "gut diversifizierter Handel, robuste Lieferketten, solide Finanzen "
            "und geringe technologische sowie energetische Abhängigkeit."
        )
    elif cluster_id == 1:
        return (
            "Cluster 1: Länder mit mittleren Risiken – "
            "gewisse Abhängigkeiten in Handel, Lieferketten oder Tech, "
            "sowie moderate Energieverwundbarkeit."
        )
    elif cluster_id == 2:
        return (
            "Cluster 2: Länder mit hohen Risiken – "
            "starke Konzentration bei Handel, Lieferketten, Tech oder Energie; "
            "hohe Anfälligkeit für externe Schocks."
        )
    return "Unbekannt"

# ------------------------------------------------------------
# 5. Länderprofil & Risiko-Storyline
# ------------------------------------------------------------

def interpret_country(scores: dict) -> str:
    lines = []

    # Makro
    if scores["macro"] > 0.66:
        lines.append("• Makroökonomisch ist das Land stark verwundbar.")
    elif scores["macro"] > 0.33:
        lines.append("• Makroökonomisch bestehen moderate Risiken.")
    else:
        lines.append("• Makroökonomisch ist das Land stabil.")

    # Geo
    if scores["geo"] > 0.66:
        lines.append("• Geopolitisch ist das Land hohen Risiken ausgesetzt.")
    elif scores["geo"] > 0.33:
        lines.append("• Geopolitisch bestehen moderate Risiken.")
    else:
        lines.append("• Geopolitisch ist das Land stabil.")

    # Governance
    if scores["governance"] > 0.66:
        lines.append("• Governance-Risiken sind hoch.")
    elif scores["governance"] > 0.33:
        lines.append("• Governance-Risiken sind moderat.")
    else:
        lines.append("• Governance-Strukturen sind stabil.")

    # Tech
    if scores["tech"] > 0.66:
        lines.append("• Technologisch besteht starke Abhängigkeit (Halbleiter, Cloud, IP, Schlüsseltechnologien).")
    elif scores["tech"] > 0.33:
        lines.append("• Technologische Abhängigkeiten sind moderat.")
    else:
        lines.append("• Technologisch ist das Land gut diversifiziert.")

    # Energie
    if scores["energie"] > 0.75:
        lines.append("• Die Energieabhängigkeit ist kritisch – starke Importabhängigkeit und hohe Verwundbarkeit bei Schocks.")
    elif scores["energie"] > 0.5:
        lines.append("• Die Energieabhängigkeit ist moderat – Diversifizierung wäre sinnvoll.")
    else:
        lines.append("• Die Energieabhängigkeit ist gering – hohe energetische Resilienz.")

    return "\n".join(lines)


def generate_country_profile(country: str, presets: dict):
    scores = compute_risk_scores(presets[country])

    text = f"## Länderprofil: {country}\n\n"
    text += f"**Makro-Risiko:** {scores['macro']:.2f}\n"
    text += f"**Geo-Risiko:** {scores['geo']:.2f}\n"
    text += f"**Governance-Risiko:** {scores['governance']:.2f}\n"
    text += f"**Handelsrisiko:** {scores['handel']:.2f}\n"
    text += f"**Lieferkettenrisiko:** {scores['supply_chain']:.2f}\n"
    text += f"**Finanzrisiko:** {scores['financial']:.2f}\n"
    text += f"**Tech-Risiko:** {scores['tech']:.2f}\n"
    text += f"**Energieabhängigkeit:** {scores['energie']:.2f}\n\n"

    text += "### Gesamtinterpretation\n"
    text += interpret_country(scores)

    return text

# ------------------------------------------------------------
# 6. Dashboard-KPIs
# ------------------------------------------------------------

def dashboard_kpis(country: str):
    scores = compute_risk_scores(presets[country])
    total_risk = scores.get("total", np.mean(list(scores.values())))

    kpi_text = (
        f"### KPI-Übersicht für {country}\n\n"
        f"- Gesamt-Risiko (falls vorhanden): **{total_risk:.2f}**\n"
        f"- Makro: **{scores['macro']:.2f}**\n"
        f"- Geo: **{scores['geo']:.2f}**\n"
        f"- Governance: **{scores['governance']:.2f}**\n"
        f"- Tech: **{scores['tech']:.2f}**\n"
        f"- Energie: **{scores['energie']:.2f}**\n"
    )

    risk_fig = plot_risk_radar(scores)

    return kpi_text, risk_fig


# ------------------------------------------------------------
# 7. Gradio-App Layout
# ------------------------------------------------------------

def build_app():

    with gr.Blocks() as demo:

        gr.Markdown("# Makro-Risiko-Dashboard")
        gr.Markdown(
            "Dieses Dashboard bündelt Simulation, Radar-Analysen, Heatmaps, "
            "Clusteranalysen und Länderprofile in einer Oberfläche."
        )

        with gr.Tab("Dashboard"):
            gr.Markdown("## Überblick & KPIs")

            dash_country = gr.Dropdown(list(presets.keys()), label="Land auswählen")
            dash_button = gr.Button("KPIs aktualisieren")
            dash_kpi_output = gr.Markdown()
            dash_radar_output = gr.Plot()

            dash_button.click(
                fn=dashboard_kpis,
                inputs=[dash_country],
                outputs=[dash_kpi_output, dash_radar_output],
            )
            with gr.Accordion("Interpretation", open=False):
                    gr.Markdown(f"```\n{dashboard_text}\n```")


        with gr.Tab("Simulation & Radar"):
            gr.Markdown("## Simulation & Radar-Analysen")
            gr.Markdown(
                "Dieser Bereich bietet Risiko-Radare für einzelne Länder, "
                "Vergleiche zwischen zwei Ländern, Multi-Radare und Delta-Analysen."
            )


            # Hier kannst du deine bestehenden Slider & Simulation einbauen.
            # Beispiel-Platzhalter:
            sim_country = gr.Dropdown(list(presets.keys()), label="Land auswählen",value=list(presets.keys())[0],)
            with gr.Accordion("📊 Risiko‑Radar (Einzelland)", open=False):
                sim_risk_button = gr.Button("📊 Risiko‑Radar anzeigen", variant="primary")
                sim_risk_output = gr.Plot()

                sim_risk_button.click(
                    lambda land: plot_risk_radar(compute_risk_scores(presets[land])),
                    inputs=[sim_country],
                    outputs=sim_risk_output,
                )
                with gr.Accordion("Risiko‑Radar ", open=False):
                    gr.Markdown(f"```\n{technologische_abhaengigkeit_text}\n```")
                    gr.Markdown(f"```\n{resilienz_radar_text}\n```")


            with gr.Accordion("🌐 Multi‑Risiko‑Radar (alle Länder)", open=False):
                sim_multi_button = gr.Button("🌐 Länder‑Vergleichs‑Radar", variant="secondary")
                sim_multi_output = gr.Plot()

                sim_multi_button.click(
                    lambda: plot_multi_risk_radar(presets),
                    inputs=None,
                    outputs=sim_multi_output,
                )
                with gr.Accordion("Multi‑Risiko‑Radar ", open=False):
                    gr.Markdown(f"```\n{status_radar_text}\n```")


            with gr.Accordion("⚖️ Vergleich: Land A vs. Land B", open=False):
                compare_country_a = gr.Dropdown(list(presets.keys()), label="Land A")
                compare_country_b = gr.Dropdown(list(presets.keys()), label="Land B")

                sim_compare_button = gr.Button("⚖️ Vergleich: Land A vs. Land B", variant="secondary")
                sim_compare_output = gr.Plot()

                sim_compare_button.click(
                    plot_compare_radar,
                    inputs=[compare_country_a, compare_country_b],
                    outputs=sim_compare_output,
                )

                with gr.Accordion("Vergleich", open=False):
                    gr.Markdown(f"```\n{benchmarking_text}\n```")


        with gr.Tab("Heatmaps"):

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

            # Annahme: ui_heatmap() existiert und liefert die Datenliste
            heat_button.click(
                fn=ui_heatmap,
                inputs=None,
                outputs=heat_output
            )

            with gr.Accordion("Interpretation", open=False):
                gr.Markdown(f"```\n{heatmap_text}\n```")

            gr.Markdown("### 2) Tech-Risiko-Heatmap")

            tech_button = gr.Button("Tech-Heatmap aktualisieren")
            tech_output = gr.Dataframe(
                headers=["Land", "Tech-Risiko", "Ampel"],
                wrap=True,
                label="Tech-Risiko-Heatmap",
            )

            tech_button.click(
                fn=lambda: tech_heatmap(presets),
                inputs=None,
                outputs=tech_output
            )

            gr.Markdown("### 3) Cluster-Heatmap: Handel + Lieferkette + Finanzen + Tech + Energie")

            cluster_heatmap_button = gr.Button("Cluster-Heatmap erzeugen")
            cluster_heatmap_output = gr.Plot()

            cluster_heatmap_button.click(
                lambda: plot_cluster_heatmap(presets),
                None,
                cluster_heatmap_output
            )

        with gr.Tab("Clusteranalyse"):
            gr.Markdown("## Clusteranalyse: Handel + Lieferketten + Finanzen + Tech + Energie")

            cluster_button = gr.Button("Cluster berechnen")
            cluster_output = gr.Dataframe(
                headers=["Land", "Cluster", "Interpretation"],
                wrap=True,
                label="Cluster-Ergebnisse",
            )

            def ui_cluster():
                countries, labels = cluster_risk_dimensions(presets)
                return [
                    [land, int(label), interpret_cluster(int(label))]
                    for land, label in zip(countries, labels)
                ]

            cluster_button.click(ui_cluster, None, cluster_output)

            gr.Markdown("### Cluster-Radar (Durchschnittswerte pro Cluster)")

            cluster_radar_button = gr.Button("Cluster-Radar erzeugen")
            cluster_radar_output = gr.Plot()

            cluster_radar_button.click(
                lambda: plot_cluster_radar(presets),
                None,
                cluster_radar_output
            )

            gr.Markdown("### Cluster-Storyline")

            story_cluster = gr.Dropdown([0, 1, 2], label="Cluster auswählen")
            story_button = gr.Button("Storyline erzeugen")
            story_output = gr.Markdown()

            story_button.click(
                lambda cid: cluster_storyline(int(cid)),
                inputs=[story_cluster],
                outputs=story_output
            )

            with gr.Accordion("Interpretation", open=False):
                gr.Markdown(f"```\n{finanzielle_abhaengigkeit_text}\n```")

        with gr.Tab("Länderprofil"):
            gr.Markdown("## Automatisches Länderprofil")

            country_select = gr.Dropdown(
                list(presets.keys()),
                label="Land auswählen"
            )

            profile_button = gr.Button("Profil erzeugen")
            profile_output = gr.Markdown()

            def ui_country_profile(land):
                interpretation = interpret_country(compute_risk_scores(presets[land]))
                profile = generate_country_profile(land, presets)
                return f"{profile}\n\n---\n\n### Interpretation\n{interpretation}"

            profile_button.click(
                fn=ui_country_profile,
                inputs=[country_select],
                outputs=profile_output
            )

        with gr.Tab("Methodik"):
            gr.Markdown("## Dokumentation der Risiko-Methodik")

            try:
                method_path = ROOT.parent / "docs" / "risk_methodology.md"
                doc_text = method_path.read_text(encoding="utf-8")
            except Exception:
                doc_text = "Dokumentation nicht gefunden."

            gr.Markdown(doc_text)

        return demo


demo = build_app()

if __name__ == "__main__":
    demo.launch(theme="soft")
