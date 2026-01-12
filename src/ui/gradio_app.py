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

def generate_risk_profile(country):
    scores = compute_risk_scores(presets[country])

    # Sortiere Dimensionen nach Risiko
    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    top_risks = sorted_dims[:3]
    low_risks = sorted_dims[-3:]

    md = f"# 🇺🇳 Risiko-Profil: {country}\n"
    md += f"**Gesamt-Risiko:** {scores['total']:.2f}\n\n"

    md += "## 🔥 Top-Risikotreiber\n"
    for dim, val in top_risks:
        md += f"- **{dim}**: {val:.2f}\n"

    md += "\n## 🟢 Stärkste Bereiche\n"
    for dim, val in low_risks:
        md += f"- **{dim}**: {val:.2f}\n"

    md += "\n## 🧠 Interpretation\n"
    if scores["total"] > 0.75:
        md += "Das Land befindet sich in einem **kritischen Risikobereich**.\n"
    elif scores["total"] > 0.55:
        md += "Das Land weist ein **erhöhtes Risiko** auf.\n"
    elif scores["total"] > 0.30:
        md += "Das Land zeigt ein **moderates Risiko**.\n"
    else:
        md += "Das Land hat ein **geringes strukturelles Risiko**.\n"

    md += "\n## 🛠 Handlungsempfehlungen\n"
    md += "- Diversifikation von Handelspartnern\n"
    md += "- Reduktion kritischer Abhängigkeiten\n"
    md += "- Stärkung institutioneller Resilienz\n"
    md += "- Ausbau erneuerbarer Energien\n"

    return md

def early_warning_system(country):
    scores = compute_risk_scores(presets[country])

    warnings = []
    critical = []

    for dim, val in scores.items():
        if dim == "total":
            continue
        if val > 0.75:
            critical.append((dim, val))
        elif val > 0.55:
            warnings.append((dim, val))

    md = f"# 🚨 Frühwarnsystem für {country}\n"

    if critical:
        md += "## 🔴 Kritische Risiken\n"
        for dim, val in critical:
            md += f"- **{dim}**: {val:.2f}\n"
    else:
        md += "## 🔴 Kritische Risiken\nKeine.\n"

    if warnings:
        md += "\n## 🟠 Erhöhte Risiken\n"
        for dim, val in warnings:
            md += f"- **{dim}**: {val:.2f}\n"
    else:
        md += "\n## 🟠 Erhöhte Risiken\nKeine.\n"

    md += "\n## 🟢 Stabilitätsindikatoren\n"
    stable = [d for d in scores if scores[d] < 0.30 and d != "total"]
    if stable:
        for dim in stable:
            md += f"- **{dim}**: {scores[dim]:.2f}\n"
    else:
        md += "Keine besonders stabilen Bereiche.\n"

    return md

def apply_scenario(country, scenario):
    base = presets[country].copy()

    if scenario == "Ölpreis +50%":
        base["energie"] = min(1.0, base["energie"] + 0.15)

    elif scenario == "USD-Zinsanstieg":
        base["financial"] = min(1.0, base["financial"] + 0.12)
        base["macro"] = min(1.0, base["macro"] + 0.08)

    elif scenario == "Sanktionen":
        base["geo"] = min(1.0, base["geo"] + 0.20)
        base["handel"] = min(1.0, base["handel"] + 0.10)

    elif scenario == "Lieferketten-Blockade":
        base["supply_chain"] = min(1.0, base["supply_chain"] + 0.25)
        base["tech"] = min(1.0, base["tech"] + 0.10)

    scores = compute_risk_scores(base)
    return plot_risk_radar(scores)


def benchmarking_table():
    rows = []
    for country in presets:
        scores = compute_risk_scores(presets[country])
        rows.append((country, scores["total"]))

    rows = sorted(rows, key=lambda x: x[1], reverse=True)

    md = "# 🌍 Benchmarking\n\n"
    md += "| Land | Risiko |\n|------|--------|\n"
    for c, s in rows:
        md += f"| {c} | {s:.2f} |\n"

    return md

def plot_heatmap():
    dims = ["macro","geo","governance","handel","supply_chain","financial","tech","energie"]

    data = []
    labels = []

    for country in presets:
        scores = compute_risk_scores(presets[country])
        row = [scores[d] for d in dims]
        data.append(row)
        labels.append(country)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data, cmap="Reds", vmin=0, vmax=1)

    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels(dims, rotation=45, ha="right")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)

    fig.colorbar(im, ax=ax)
    return fig

def storyline_v2(country):
    scores = compute_risk_scores(presets[country])

    dims_sorted = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = dims_sorted[:3]
    low = dims_sorted[-2:]

    md = f"# 🧠 Storyline 2.0 – {country}\n"

    md += "## 🔥 Haupttreiber des Risikos\n"
    for d, v in top:
        if d != "total":
            md += f"- **{d}**: {v:.2f}\n"

    md += "\n## 🟢 Stabilitätsanker\n"
    for d, v in low:
        if d != "total":
            md += f"- **{d}**: {v:.2f}\n"

    md += "\n## 📘 Narrative Analyse\n"
    md += "Das Land zeigt eine komplexe Risikostruktur. "
    md += f"Besonders prägend sind die Dimensionen **{top[0][0]}** und **{top[1][0]}**, "
    md += "die das Gesamtbild dominieren. "
    md += "Gleichzeitig wirken stabile Bereiche wie "
    md += f"**{low[0][0]}** als Puffer gegen externe Schocks.\n"

    md += "\n## 🛠 Handlungsempfehlungen\n"
    md += "- Diversifikation kritischer Abhängigkeiten\n"
    md += "- Stärkung institutioneller Resilienz\n"
    md += "- Ausbau erneuerbarer Energien\n"
    md += "- Reduktion geopolitischer Verwundbarkeit\n"

    return md

# ============================================================
# RADAR-FUNKTIONEN
# ============================================================

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


def interpret_dashboard_old(params: dict, scores: dict) -> str:
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

        
        with gr.Tab("Risiko-Profil & Frühwarnsystem"):

            gr.Markdown("## 📊 Risiko-Profil & 🚨 Frühwarnsystem")

            country_select = gr.Dropdown(
                list(presets.keys()),
                label="Land auswählen",
                value=list(presets.keys())[0]
            )

            with gr.Accordion("📘 Risiko-Profil (Markdown)", open=True):
                profile_button = gr.Button("📄 Risiko-Profil generieren", variant="primary")
                profile_output = gr.Markdown()

                profile_button.click(
                    generate_risk_profile,
                    inputs=[country_select],
                    outputs=profile_output
                )

            with gr.Accordion("🚨 Early-Warning-System", open=False):
                ews_button = gr.Button("⚠️ Frühwarnsystem anzeigen", variant="secondary")
                ews_output = gr.Markdown()

                ews_button.click(
                    early_warning_system,
                    inputs=[country_select],
                    outputs=ews_output
                )
        
        with gr.Tab("Szenarien & Analyse"):
            gr.Markdown("## 🔮 Szenarien, Benchmarking, Heatmap & Storyline 2.0")
            country_sel = gr.Dropdown(list(presets.keys()), label="Land", value=list(presets.keys())[0])

            # Szenario-Modul
            with gr.Accordion("🧨 Szenario-Simulation", open=False):
                scenario = gr.Dropdown(
                    ["Ölpreis +50%", "USD-Zinsanstieg", "Sanktionen", "Lieferketten-Blockade"],
                    label="Szenario auswählen"
                )
                scenario_btn = gr.Button("Szenario anwenden", variant="primary")
                scenario_out = gr.Plot()

                scenario_btn.click(
                    apply_scenario,
                    inputs=[country_sel, scenario],
                    outputs=scenario_out
                )

            # Benchmarking
            with gr.Accordion("🌍 Benchmarking", open=False):
                bench_btn = gr.Button("Benchmarking anzeigen")
                bench_out = gr.Markdown()

                bench_btn.click(
                    lambda: benchmarking_table(),
                    inputs=None,
                    outputs=bench_out
                )

            # Heatmap
            with gr.Accordion("🔥 Risiko-Heatmap", open=False):
                heat_btn = gr.Button("Heatmap anzeigen")
                heat_out = gr.Plot()

                heat_btn.click(
                    lambda: plot_heatmap(),
                    inputs=None,
                    outputs=heat_out
                )

            # Storyline 2.0
            with gr.Accordion("🧠 Storyline 2.0", open=False):
                story_btn = gr.Button("Storyline generieren")
                story_out = gr.Markdown()

                story_btn.click(
                    storyline_v2,
                    inputs=[country_sel],
                    outputs=story_out
                ) 

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
