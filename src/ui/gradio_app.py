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

EXPECTED_COUNTRIES = ["DE", "US", "IR", "CN", "FR", "IN", "BR", "GR", "GB"]

# ---------------------------------------------------------
#  RISIKO-DIMENSIONEN & GEWICHTE
# ---------------------------------------------------------

RISK_KEYS = [
    "macro",
    "geo",
    "governance",
    "handel",
    "supply_chain",
    "currency",
    "political_security",
    "financial",
    "tech",
    "energie",
]

WEIGHTS = {
    "macro": 0.22,
    "geo": 0.18,
    "governance": 0.15,
    "handel": 0.10,
    "supply_chain": 0.06,
    "currency": 0.07,
    "financial": 0.06,
    "tech": 0.05,
    "energie": 0.05,
    "political_security": 0.06,
}

# ---------------------------------------------------------
#  ALIAS-MAPPING
# ---------------------------------------------------------

KEY_ALIASES = {
    "macroeconomic": "macro",
    "geopolitical": "geo",
    "gov": "governance",
    "trade": "handel",
    "supplychain": "supply_chain",
    "supply_chain_risk": "supply_chain",
    "finanz": "financial",
    "finance": "financial",
    "technology": "tech",
    "energy": "energie",

    # Währungs- und Zahlungsabhängigkeit
    "currency_risk": "currency",
    "currency": "currency",
    "fx": "currency",
    "fx_risk": "currency",
    "waehrung": "currency",
    "waehrungsabhaengigkeit": "currency",
    "payment": "currency",
    "payment_risk": "currency",
    "swift": "currency",
    "swift_risk": "currency",
}

SCENARIO_METADATA = {
    "Ölpreis-Schock": {
        "description": "Starker Anstieg der Ölpreise",
        "params_info": "Intensität 0–1, wirkt v.a. auf Energie & Makro",
    },
    "USD-Zinsanstieg": {
        "description": "Anstieg der US-Leitzinsen",
        "params_info": "Intensität 0–1, wirkt auf Finanzen & Makro",
    },
    "Sanktionen": {
        "description": "Handels- und Finanzsanktionen",
        "params_info": "Intensität 0–1, wirkt auf Geo & Handel",
    },
    "Lieferketten-Blockade": {
        "description": "Störung globaler Lieferketten",
        "params_info": "Intensität 0–1, wirkt auf Supply Chain & Tech",
    },
    "Energieembargo": {
        "description": "Starke Einschränkung von Energieimporten",
        "params_info": "Intensität 0–1, wirkt auf Energie & Geo",
    },
    "Bankenkrise": {
        "description": "Stress im Bankensystem",
        "params_info": "Intensität 0–1, wirkt auf Finanzen & Makro",
    },
    "Cyberangriff": {
        "description": "Schwere Cyberangriffe auf kritische Infrastruktur",
        "params_info": "Intensität 0–1, wirkt auf Tech & Governance",
    },
    "Dollar-Schock": {
        "description": "Starke USD-Aufwertung und Zinsanstieg",
        "params_info": "Intensität 0–1, wirkt auf Currency, Finanzen & Makro",
    },
    "SWIFT-Ausschluss": {
        "description": "Ausschluss oder Einschränkung des Zugangs zu SWIFT",
        "params_info": "Intensität 0–1, wirkt auf Currency, Handel & Geo",
    },
}

scenario_presets = {
    "Russland-Sanktionen": {
        "Sanktionen": 0.9,
        "SWIFT-Ausschluss": 0.8,
        "Dollar-Schock": 0.3,
    },
    "Ölpreis-Schock 150%": {
        "Ölpreis-Schock": 1.0,
        "Energieembargo": 0.4,
    },
    "Bankenstress": {
        "Bankenkrise": 0.8,
        "USD-Zinsanstieg": 0.6,
    },
}

SCENARIO_ORDER = [
    "Ölpreis-Schock",
    "USD-Zinsanstieg",
    "Sanktionen",
    "Lieferketten-Blockade",
    "Energieembargo",
    "Bankenkrise",
    "Cyberangriff",
    "Dollar-Schock",
    "SWIFT-Ausschluss",
]

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

# ---------------------------------------------------------
#  NORMALISIERUNG & ensure_full_risk_vector
# ---------------------------------------------------------

def normalize_value(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, v))

def ensure_full_risk_vector(base: dict) -> dict:
    """
    Stellt sicher, dass alle Risiko-Dimensionen vorhanden sind.
    Ergänzt fehlende Keys, wendet Aliase an und normalisiert Werte.
    """
    base = base.copy()

    for old, new in KEY_ALIASES.items():
        if old in base:
            base[new] = base[old]

    for key in RISK_KEYS:
        if key not in base:
            base[key] = 0.0

    for key in RISK_KEYS:
        base[key] = normalize_value(base[key])

    for key in [
        "sicherheitsgarantien",
        "aussenpolitische_abhaengigkeit",
        "externer_einfluss",
        "sanktionsverwundbarkeit",
        "diplomatische_resilienz",
    ]:
        if key not in base:
            base[key] = 0.5  # neutraler Default   

    for key in [
        "strategische_autonomie"
    ]:
        if key not in base:
            base[key] = 0.5
    
    return base

def validate_all_presets(presets: dict):
    report_lines = []
    fixed_presets = {}

    for country, data in presets.items():
        original_keys = set(data.keys())
        fixed = ensure_full_risk_vector(data)
        fixed_presets[country] = fixed
        new_keys = set(fixed.keys())

        added = new_keys - original_keys
        aliased = [k for k in KEY_ALIASES if k in original_keys]

        line = f"- {country}: hinzugefügt: {list(added)}"
        if aliased:
            line += f" | Aliase genutzt: {aliased}"
        report_lines.append(line)

    report = "# ✅ Preset-Validierung\n\n"
    report += "Die folgenden Anpassungen wurden vorgenommen:\n\n"
    report += "\n".join(report_lines)

    return fixed_presets, report

# ============================================================
# HILFSFUNKTIONEN FÜR DIE SIMULATION / PROFILE / EWS
# ============================================================

def generate_risk_profile(country):
    base_vec = ensure_full_risk_vector(presets[country])
    scores = compute_risk_scores(base_vec)

    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    top_risks = [d for d in sorted_dims if d[0] != "total"][:3]
    low_risks = [d for d in sorted_dims if d[0] != "total"][-3:]

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

def ews_from_scores(scores: dict, title: str = "Frühwarnsystem"):
    warnings = []
    critical = []

    for dim, val in scores.items():
        if dim == "total":
            continue
        if val > 0.75:
            critical.append((dim, val))
        elif val > 0.55:
            warnings.append((dim, val))

    md = f"# 🚨 {title}\n"

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
    stable = [d for d in scores if d != "total" and scores[d] < 0.30]
    if stable:
        for dim in stable:
            md += f"- **{dim}**: {scores[dim]:.2f}\n"
    else:
        md += "Keine besonders stabilen Bereiche.\n"

    if "currency" in scores:
        if scores["currency"] > 0.75:
            md += (
                "\n## ⚠️ Spezielle Warnung: Währungs- & Zahlungsabhängigkeit\n"
                f"- Die Abhängigkeit von Leitwährungen und Zahlungssystemen ist **kritisch hoch** "
                f"({scores['currency']:.2f}).\n"
                "- Risiko: Hohe USD-Exposure, SWIFT-Abhängigkeit, mögliche Sanktionen.\n"
            )
        elif scores["currency"] > 0.55:
            md += (
                "\n## ⚠️ Hinweis: Erhöhte Währungsabhängigkeit\n"
                f"- Die Währungs- und Zahlungsabhängigkeit ist **erhöht** "
                f"({scores['currency']:.2f}).\n"
                "- Risiko: Sensitivität gegenüber USD-Zins- und Wechselkurspolitik.\n"
            )

    if "political_security" in scores:
        if scores["political_security"] > 0.75:
            md += (
                "\n## ⚠️ Spezielle Warnung: Politische & sicherheitspolitische Abhängigkeit\n"
                f"- Die politische und sicherheitspolitische Abhängigkeit ist **kritisch hoch** "
                f"({scores['political_security']:.2f}).\n"
                "- Risiko: Eingeschränkte strategische Autonomie, hohe Verwundbarkeit gegenüber Sanktionen und Druck.\n"
            )
        elif scores["political_security"] > 0.55:
            md += (
                "\n## ⚠️ Hinweis: Erhöhte politische Abhängigkeit\n"
                f"- Die politische und sicherheitspolitische Abhängigkeit ist **erhöht** "
                f"({scores['political_security']:.2f}).\n"
                "- Risiko: Relevante Verwundbarkeit gegenüber externem Druck.\n"
            )

    return md

def early_warning_system(country):
    base_vec = ensure_full_risk_vector(presets[country])
    scores = compute_risk_scores(base_vec)
    return ews_from_scores(scores, title=f"Frühwarnsystem – {country}")

# ============================================================
# SZENARIEN / SHOCK-ENGINE
# ============================================================

def apply_scenario(country, scenario):
    base = ensure_full_risk_vector(presets[country])

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
        base_vec = ensure_full_risk_vector(presets[country])
        scores = compute_risk_scores(base_vec)
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
        base_vec = ensure_full_risk_vector(presets[country])
        scores = compute_risk_scores(base_vec)
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
    base_vec = ensure_full_risk_vector(presets[country])
    scores = compute_risk_scores(base_vec)

    dims_sorted = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = [d for d in dims_sorted if d[0] != "total"][:3]
    low = [d for d in dims_sorted if d[0] != "total"][-2:]

    md = f"# 🧠 Storyline 2.0 – {country}\n"

    md += "## 🔥 Haupttreiber des Risikos\n"
    for d, v in top:
        md += f"- **{d}**: {v:.2f}\n"

    md += "\n## 🟢 Stabilitätsanker\n"
    for d, v in low:
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

def storyline_v3(country):
    scores = compute_risk_scores(presets[country])

    dims_sorted = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = dims_sorted[:3]
    low = dims_sorted[-2:]

    ps = scores["political_security"]
    sa = scores["strategische_autonomie"]

    md = f"# 🧠 Storyline 3.0 – {country}\n"

    md += "## 🔥 Haupttreiber des Risikos\n"
    for d, v in top:
        if d not in ("total", "strategische_autonomie"):
            md += f"- **{d}**: {v:.2f}\n"

    md += "\n## 🟢 Stabilitätsanker\n"
    for d, v in low:
        if d not in ("total", "political_security"):
            md += f"- **{d}**: {v:.2f}\n"

    md += "\n## 🛡 Politische Abhängigkeit & Autonomie\n"
    if ps > 0.75:
        md += "- Das Land weist eine **kritisch hohe politische Abhängigkeit** auf.\n"
    elif ps > 0.55:
        md += "- Das Land zeigt eine **erhöhte politische Abhängigkeit**.\n"
    else:
        md += "- Die politische Abhängigkeit ist **moderat bis gering**.\n"

    if sa > 0.75:
        md += "- Die **strategische Autonomie** ist sehr hoch – das Land kann souverän handeln.\n"
    elif sa > 0.50:
        md += "- Die strategische Autonomie ist **solide**, aber nicht vollständig.\n"
    else:
        md += "- Die strategische Autonomie ist **eingeschränkt** – externe Akteure beeinflussen Entscheidungen.\n"

    md += "\n## 📘 Narrative Analyse\n"
    md += (
        "Das Land zeigt eine komplexe Risikostruktur. "
        f"Besonders prägend sind die Dimensionen **{top[0][0]}** und **{top[1][0]}**, "
        "die das Gesamtbild dominieren. "
        "Gleichzeitig wirken stabile Bereiche als Puffer gegen externe Schocks. "
        "Die Balance zwischen politischer Abhängigkeit und strategischer Autonomie "
        "prägt die langfristige Handlungsfähigkeit des Landes.\n"
    )

    md += "\n## 🛠 Handlungsempfehlungen\n"
    md += "- Reduktion politischer Abhängigkeiten\n"
    md += "- Ausbau strategischer Autonomie (Diplomatie, Industrie, Energie)\n"
    md += "- Diversifikation kritischer Abhängigkeiten\n"
    md += "- Stärkung institutioneller Resilienz\n"

    return md  

def autonomy_heatmap(presets):
    rows = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        a = scores["strategische_autonomie"]

        if a > 0.75:
            color = "🟢"   # hohe Autonomie
        elif a > 0.50:
            color = "🟡"   # mittlere Autonomie
        else:
            color = "🔴"   # niedrige Autonomie

        rows.append([land, round(a, 3), color])

    return rows

def apply_single_shock(base: dict, shock_type: str, intensity: float) -> dict:
    base = ensure_full_risk_vector(base)
    f = max(0.0, min(1.0, float(intensity)))

    if shock_type == "Ölpreis-Schock":
        base["energie"] = min(1.0, base["energie"] + 0.25 * f)
        base["macro"] = min(1.0, base["macro"] + 0.10 * f)

    elif shock_type == "USD-Zinsanstieg":
        base["financial"] = min(1.0, base["financial"] + 0.20 * f)
        base["macro"] = min(1.0, base["macro"] + 0.10 * f)

    elif shock_type == "Sanktionen":
        base["geo"] = min(1.0, base["geo"] + 0.25 * f)
        base["handel"] = min(1.0, base["handel"] + 0.15 * f)

    elif shock_type == "Lieferketten-Blockade":
        base["supply_chain"] = min(1.0, base["supply_chain"] + 0.30 * f)
        base["tech"] = min(1.0, base["tech"] + 0.10 * f)

    elif shock_type == "Energieembargo":
        base["energie"] = min(1.0, base["energie"] + 0.35 * f)
        base["geo"] = min(1.0, base["geo"] + 0.10 * f)

    elif shock_type == "Bankenkrise":
        base["financial"] = min(1.0, base["financial"] + 0.30 * f)
        base["macro"] = min(1.0, base["macro"] + 0.15 * f)

    elif shock_type == "Cyberangriff":
        base["tech"] = min(1.0, base["tech"] + 0.25 * f)
        base["governance"] = min(1.0, base["governance"] + 0.10 * f)

    elif shock_type == "Dollar-Schock":
        base["currency"] = min(1.0, base["currency"] + 0.30 * f)
        base["financial"] = min(1.0, base["financial"] + 0.15 * f)
        base["macro"] = min(1.0, base["macro"] + 0.10 * f)

    elif shock_type == "SWIFT-Ausschluss":
        base["currency"] = min(1.0, base["currency"] + 0.35 * f)
        base["handel"] = min(1.0, base["handel"] + 0.20 * f)
        base["geo"] = min(1.0, base["geo"] + 0.20 * f)

    elif shock_type == "Sanktionen":
        base["sanktionsverwundbarkeit"] += 0.25 * f
        base["aussenpolitische_abhaengigkeit"] += 0.10 * f

    elif shock_type == "SWIFT-Ausschluss":
        base["sanktionsverwundbarkeit"] += 0.30 * f
        base["externer_einfluss"] += 0.15 * f

    elif shock_type == "Dollar-Schock":
        base["aussenpolitische_abhaengigkeit"] += 0.10 * f

    return base

def apply_multiple_shocks(country: str, shocks: List[Tuple[str, float]]) -> dict:
    base = ensure_full_risk_vector(presets[country])
    for shock_type, intensity in shocks:
        base = apply_single_shock(base, shock_type, intensity)
    return base

def apply_multiple_shocks_for_country(country: str, shock_config: dict) -> dict:
    base = ensure_full_risk_vector(presets[country])
    for shock_type, intensity in shock_config.items():
        if intensity is None or intensity == 0:
            continue
        base = apply_single_shock(base, shock_type, intensity)
    return base

# ============================================================
# DELTA-EWS / SZENARIO-REPORTING
# ============================================================

def delta_ews_panel(scores_base: dict, scores_scen: dict) -> str:
    def level(v: float) -> str:
        if v > 0.75:
            return "critical"
        if v > 0.55:
            return "warning"
        return "normal"

    newly_critical = []
    newly_warning = []
    deescalated = []

    for dim, base_val in scores_base.items():
        if dim == "total":
            continue
        scen_val = scores_scen.get(dim, base_val)
        base_lvl = level(base_val)
        scen_lvl = level(scen_val)

        if base_lvl != "critical" and scen_lvl == "critical":
            newly_critical.append((dim, base_val, scen_val))
        elif base_lvl == "normal" and scen_lvl == "warning":
            newly_warning.append((dim, base_val, scen_val))
        elif base_lvl in ("critical", "warning") and scen_lvl == "normal":
            deescalated.append((dim, base_val, scen_val))

    md = "## 🔺 Delta‑Frühwarnsystem\n\n"

    md += "### 🔴 Neu kritisch geworden\n"
    if newly_critical:
        for dim, b, s in newly_critical:
            md += f"- **{dim}**: {b:.2f} → **{s:.2f}**\n"
    else:
        md += "- Keine Dimension neu kritisch.\n"

    md += "\n### 🟠 Neu erhöht (aber nicht kritisch)\n"
    if newly_warning:
        for dim, b, s in newly_warning:
            md += f"- **{dim}**: {b:.2f} → **{s:.2f}**\n"
    else:
        md += "- Keine Dimension neu erhöht.\n"

    md += "\n### 🟢 Entschärft\n"
    if deescalated:
        for dim, b, s in deescalated:
            md += f"- **{dim}**: {b:.2f} → **{s:.2f}**\n"
    else:
        md += "- Keine Dimension deutlich entschärft.\n"

    return md

def load_scenario_preset(preset_name: str):
    if not preset_name or preset_name not in scenario_presets:
        return [0.0] * len(SCENARIO_ORDER)

    config = scenario_presets[preset_name]
    values = []
    for shock in SCENARIO_ORDER:
        values.append(float(config.get(shock, 0.0)))
    return values

def plot_scenario_compare_radar(scores_base: dict, scores_scenario: dict):
    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
    ]

    dims = [
        "macro", "geo", "governance", "handel",
        "supply_chain", "financial", "tech", "energie",
        "currency", "political_security", "strategische_autonomie"
    ]

    v_base = [scores_base[d] for d in dims]
    v_scen = [scores_scenario[d] for d in dims]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.set_ylim(0, 1)

    ax.plot(angles, v_base + [v_base[0]], label="Baseline", linewidth=2, color="grey")
    ax.fill(angles, v_base + [v_base[0]], alpha=0.1, color="grey")

    ax.plot(angles, v_scen + [v_scen[0]], label="Szenario", linewidth=2, color="red")
    ax.fill(angles, v_scen + [v_scen[0]], alpha=0.2, color="red")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.legend(loc="upper right")

    return fig

def scenario_report(country: str, scores_base: dict, scores_scen: dict, shock_config: dict) -> str:
    dims_order = [
        "macro", "geo", "governance", "handel",
        "supply_chain", "financial", "tech", "energie",
        "currency", "political_security"
    ]
    dim_names = {
        "macro": "Makroökonomie",
        "geo": "Geopolitik",
        "governance": "Governance",
        "handel": "Handel",
        "supply_chain": "Lieferkette",
        "financial": "Finanzen",
        "tech": "Technologie",
        "energie": "Energie",
        "currency": "Währungsabhängigkeit",
        "political_security": "Politische & sicherheitspolitische Abhängigkeit",
    }

    md = f"# 📊 Szenario-Report – {country}\n\n"
    md += f"**Baseline-Gesamtrisiko:** {scores_base['total']:.2f}\n\n"
    md += f"**Szenario-Gesamtrisiko:** {scores_scen['total']:.2f}\n\n"

    delta_total = scores_scen["total"] - scores_base["total"]
    md += f"**Δ Gesamtrisiko:** {delta_total:+.2f}\n\n"

    md += "## 🔧 Eingesetzte Schocks\n"
    if not shock_config:
        md += "- Keine Schocks aktiv.\n\n"
    else:
        for shock, intensity in shock_config.items():
            if intensity and intensity > 0:
                meta = SCENARIO_METADATA.get(shock, {})
                desc = meta.get("description", "")
                md += f"- **{shock}** (Intensität: {intensity:.2f}) – {desc}\n"
        md += "\n"

    md += "## 📈 Veränderung nach Dimension\n\n"
    md += "| Dimension | Baseline | Szenario | Δ |\n"
    md += "|-----------|----------|----------|----|\n"
    for d in dims_order:
        db = scores_base[d]
        ds = scores_scen[d]
        dd = ds - db
        md += f"| {dim_names[d]} | {db:.2f} | {ds:.2f} | {dd:+.2f} |\n"
    md += "\n"

    deltas = [
        (dim_names[d], scores_scen[d] - scores_base[d])
        for d in dims_order
    ]
    deltas_sorted = sorted(deltas, key=lambda x: x[1], reverse=True)

    md += "## 🔥 Stärkste Risikoanstiege\n"
    for name, d in deltas_sorted[:3]:
        if d > 0:
            md += f"- **{name}**: {d:+.2f}\n"
    if all(d <= 0 for _, d in deltas_sorted):
        md += "- Keine signifikanten Risikoanstiege.\n"
    md += "\n"

    md += "## 🧠 Kurzinterpretation\n"
    if delta_total > 0.15:
        md += "Das Szenario führt zu einem **deutlich erhöhten strukturellen Risiko**.\n"
    elif delta_total > 0.05:
        md += "Das Szenario erhöht das Gesamtrisiko **spürbar, aber moderat**.\n"
    elif delta_total > 0:
        md += "Das Szenario erhöht das Gesamtrisiko **nur leicht**.\n"
    else:
        md += "Das Szenario hat **keine oder sogar leicht entlastende Wirkung** auf das Gesamtrisiko.\n"

    md += "\n## 🛠 Mögliche Handlungsempfehlungen\n"
    md += "- Diversifikation kritischer Abhängigkeiten (Handel, Energie, Lieferketten)\n"
    md += "- Stärkung institutioneller Resilienz und Governance\n"
    md += "- Aufbau von Pufferkapazitäten in Lieferketten und Energieversorgung\n"
    md += "- Reduktion finanzieller Verwundbarkeiten (Verschuldung, externe Finanzierung)\n"

    return md

def scenario_summary(scores_base: dict, scores_scen: dict, shock_config: dict) -> str:
    delta_total = scores_scen["total"] - scores_base["total"]

    md = "## 📊 Szenario – Kurz-Auswertung\n\n"
    md += f"**Δ Gesamtrisiko:** {delta_total:+.2f}\n\n"

    active = {k: v for k, v in shock_config.items() if v and v > 0}
    if active:
        md += "### 🔧 Aktive Schocks\n"
        for shock, val in active.items():
            md += f"- **{shock}** (Intensität: {val:.2f})\n"
    else:
        md += "### 🔧 Aktive Schocks\nKeine.\n"

    md += "\n### 🔺 Stärkste Veränderungen\n"
    deltas = []
    for dim in scores_base:
        if dim == "total":
            continue
        deltas.append((dim, scores_scen[dim] - scores_base[dim]))

    deltas_sorted = sorted(deltas, key=lambda x: abs(x[1]), reverse=True)

    for dim, d in deltas_sorted[:4]:
        md += f"- **{dim}**: {scores_base[dim]:.2f} → {scores_scen[dim]:.2f} (Δ {d:+.2f})\n"

    md += "\n### 🧠 Interpretation\n"
    if delta_total > 0.15:
        md += "Das Szenario erhöht das strukturelle Risiko **deutlich**.\n"
    elif delta_total > 0.05:
        md += "Das Szenario erhöht das Risiko **moderat**.\n"
    elif delta_total > 0:
        md += "Das Szenario erhöht das Risiko **leicht**.\n"
    else:
        md += "Das Szenario **reduziert** das Gesamtrisiko leicht.\n"

    return md

def decision_support_view(country: str,
                          oil_intensity,
                          usd_intensity,
                          sanc_intensity,
                          supply_intensity,
                          energy_intensity,
                          bank_intensity,
                          cyber_intensity,
                          dollar_intensity,
                          swift_intensity):

    base_vec = ensure_full_risk_vector(presets[country])
    scores_base = compute_risk_scores(base_vec)

    shock_config = {
        "Ölpreis-Schock": oil_intensity,
        "USD-Zinsanstieg": usd_intensity,
        "Sanktionen": sanc_intensity,
        "Lieferketten-Blockade": supply_intensity,
        "Energieembargo": energy_intensity,
        "Bankenkrise": bank_intensity,
        "Cyberangriff": cyber_intensity,
        "Dollar-Schock": dollar_intensity,
        "SWIFT-Ausschluss": swift_intensity,
    }
    any_shock = any(v and v > 0 for v in shock_config.values())

    if any_shock:
        scen_vec = apply_multiple_shocks_for_country(country, shock_config)
        scores_scen = compute_risk_scores(scen_vec)
        radar_fig = plot_scenario_compare_radar(scores_base, scores_scen)
        delta_ews_md = delta_ews_panel(scores_base, scores_scen)
        scen_report = scenario_report(country, scores_base, scores_scen, shock_config)
    else:
        scores_scen = scores_base
        radar_fig = plot_risk_radar(scores_base)
        delta_ews_md = "## 🔺 Delta‑Frühwarnsystem\n\nKeine Szenario‑Änderungen aktiv."
        scen_report = scenario_report(country, scores_base, scores_base, {})

    ews_base_md = ews_from_scores(scores_base, title=f"Frühwarnsystem – Baseline ({country})")
    ews_scen_md = ews_from_scores(scores_scen, title=f"Frühwarnsystem – Szenario ({country})")

    bench_md = benchmarking_table()

    delta_total = scores_scen["total"] - scores_base["total"]
    rec_md = f"## 🧠 Decision Support – Kurzinterpretation\n\n"
    rec_md += f"- Δ Gesamtrisiko: **{delta_total:+.2f}**\n"
    if delta_total > 0.15:
        rec_md += "- Das Szenario erhöht das strukturelle Risiko deutlich.\n"
    elif delta_total > 0.05:
        rec_md += "- Das Szenario erhöht das Risiko moderat.\n"
    elif delta_total > 0:
        rec_md += "- Das Szenario erhöht das Risiko leicht.\n"
    else:
        rec_md += "- Keine relevante Erhöhung des Gesamtrisikos.\n"

    return radar_fig, ews_base_md, ews_scen_md, delta_ews_md, scen_report, bench_md, rec_md

def scenario_ranking(country: str, intensity: float = 1.0) -> str:
    base_vec = ensure_full_risk_vector(presets[country])
    scores_base = compute_risk_scores(base_vec)
    base_total = scores_base["total"]

    results = []

    for shock_name in SCENARIO_METADATA.keys():
        scen_vec = apply_multiple_shocks_for_country(country, {shock_name: intensity})
        scores_scen = compute_risk_scores(scen_vec)
        delta = scores_scen["total"] - base_total
        results.append((shock_name, delta))

    results_sorted = sorted(results, key=lambda x: x[1], reverse=True)

    md = f"## 📈 Szenario-Ranking (Einzelschocks, Intensität = {intensity:.2f}) – {country}\n\n"
    md += "| Schock | Δ Gesamtrisiko |\n"
    md += "|--------|----------------|\n"
    for shock, d in results_sorted:
        md += f"| {shock} | {d:+.2f} |\n"

    if results_sorted:
        top_shock, top_delta = results_sorted[0]
        md += "\n### Fazit\n"
        md += f"Der stärkste Einzeltreiber in diesem Land ist **{top_shock}** mit Δ Gesamtrisiko {top_delta:+.2f}.\n"

    return md

# ============================================================
# RADAR-FUNKTIONEN
# ============================================================

def tech_heatmap(presets):
    rows = []
    for land, params in presets.items():
        base_vec = ensure_full_risk_vector(params)
        scores = compute_risk_scores(base_vec)
        t = scores["tech"]

        if t < 0.33:
            color = "🟢"
        elif t < 0.66:
            color = "🟡"
        else:
            color = "🔴"

        rows.append([land, round(t, 3), color])

    return rows

def plot_risk_radar(scores: dict):
    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
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
        scores["currency"],
        scores["political_security"],
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
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
    ]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})

    for land, params in presets.items():
        base_vec = ensure_full_risk_vector(params)
        scores = compute_risk_scores(base_vec)

        values = [
            scores["macro"],
            scores["geo"],
            scores["governance"],
            scores["handel"],
            scores["supply_chain"],
            scores["financial"],
            scores["tech"],
            scores["energie"],
            scores["currency"],
            scores["political_security"],
        ]
        values = np.concatenate((values, [values[0]]))

        ax.plot(angles, values, linewidth=1.5, label=land)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return fig

def plot_compare_radar(country_a, country_b):
    base_a = ensure_full_risk_vector(presets[country_a])
    base_b = ensure_full_risk_vector(presets[country_b])
    scores_a = compute_risk_scores(base_a)
    scores_b = compute_risk_scores(base_b)

    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
    ]

    dims = [
        "macro", "geo", "governance", "handel",
        "supply_chain", "financial", "tech", "energie",
        "currency", "political_security", "strategische_autonomie"
    ]

    values_a = [scores_a[k] for k in dims]
    values_b = [scores_b[k] for k in dims]

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

# ------------------------------------------------------------
# CLUSTERANALYSE
# ------------------------------------------------------------

def cluster_risk_dimensions(presets: dict):
    countries = list(presets.keys())

    X = np.array([
        [
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["handel"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["supply_chain"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["financial"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["tech"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["energie"],
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
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["handel"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["supply_chain"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["financial"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["tech"],
            compute_risk_scores(ensure_full_risk_vector(presets[land]))["energie"],
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
            [compute_risk_scores(ensure_full_risk_vector(presets[land])[d]) for d in dims]
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
# LÄNDERPROFIL & INTERPRETATION
# ------------------------------------------------------------

def interpret_country(scores: dict) -> str:
    lines = []

    if scores["macro"] > 0.66:
        lines.append("• Makroökonomisch ist das Land stark verwundbar.")
    elif scores["macro"] > 0.33:
        lines.append("• Makroökonomisch bestehen moderate Risiken.")
    else:
        lines.append("• Makroökonomisch ist das Land stabil.")

    if scores["geo"] > 0.66:
        lines.append("• Geopolitisch ist das Land hohen Risiken ausgesetzt.")
    elif scores["geo"] > 0.33:
        lines.append("• Geopolitisch bestehen moderate Risiken.")
    else:
        lines.append("• Geopolitisch ist das Land stabil.")

    if scores["governance"] > 0.66:
        lines.append("• Governance-Risiken sind hoch.")
    elif scores["governance"] > 0.33:
        lines.append("• Governance-Risiken sind moderat.")
    else:
        lines.append("• Governance-Strukturen sind stabil.")

    if scores["tech"] > 0.66:
        lines.append("• Technologisch besteht starke Abhängigkeit (Halbleiter, Cloud, IP, Schlüsseltechnologien).")
    elif scores["tech"] > 0.33:
        lines.append("• Technologische Abhängigkeiten sind moderat.")
    else:
        lines.append("• Technologisch ist das Land gut diversifiziert.")

    if scores["energie"] > 0.75:
        lines.append("• Die Energieabhängigkeit ist kritisch – starke Importabhängigkeit und hohe Verwundbarkeit bei Schocks.")
    elif scores["energie"] > 0.5:
        lines.append("• Die Energieabhängigkeit ist moderat – Diversifizierung wäre sinnvoll.")
    else:
        lines.append("• Die Energieabhängigkeit ist gering – hohe energetische Resilienz.")

    if scores["currency"] > 0.75:
        lines.append("• Die Währungs- und Zahlungsabhängigkeit ist kritisch – hohe Verwundbarkeit gegenüber USD, SWIFT und Sanktionen.")
    elif scores["currency"] > 0.5:
        lines.append("• Die Währungsabhängigkeit ist erhöht – stärkere Diversifizierung wäre sinnvoll.")
    else:
        lines.append("• Die Währungsabhängigkeit ist gering – hohe monetäre Resilienz.")

    if scores["political_security"] > 0.75:
        lines.append("• Die politische und sicherheitspolitische Abhängigkeit ist kritisch – eingeschränkte strategische Autonomie.")
    elif scores["political_security"] > 0.5:
        lines.append("• Die politische Abhängigkeit ist erhöht – relevante Verwundbarkeit gegenüber externem Druck.")
    else:
        lines.append("• Die politische und sicherheitspolitische Autonomie ist hoch.")

    return "\n".join(lines)

def generate_country_profile(country: str, presets: dict):
    base_vec = ensure_full_risk_vector(presets[country])
    scores = compute_risk_scores(base_vec)

    text = f"## Länderprofil: {country}\n\n"
    text += f"**Makro-Risiko:** {scores['macro']:.2f}\n"
    text += f"**Geo-Risiko:** {scores['geo']:.2f}\n"
    text += f"**Governance-Risiko:** {scores['governance']:.2f}\n"
    text += f"**Handelsrisiko:** {scores['handel']:.2f}\n"
    text += f"**Lieferkettenrisiko:** {scores['supply_chain']:.2f}\n"
    text += f"**Finanzrisiko:** {scores['financial']:.2f}\n"
    text += f"**Tech-Risiko:** {scores['tech']:.2f}\n"
    text += f"**Energieabhängigkeit:** {scores['energie']:.2f}\n"
    text += f"**Währungsabhängigkeit:** {scores['currency']:.2f}\n"
    text += f"**Politische & sicherheitspolitische Abhängigkeit:** {scores['political_security']:.2f}\n\n"

    text += "### Gesamtinterpretation\n"
    text += interpret_country(scores)

    return text

def dashboard_kpis(country: str):
    base_vec = ensure_full_risk_vector(presets[country])
    scores = compute_risk_scores(base_vec)
    total_risk = scores.get("total", np.mean(list(scores.values())))

    kpi_text = (
        f"### KPI-Übersicht für {country}\n\n"
        f"- Gesamt-Risiko (falls vorhanden): **{total_risk:.2f}**\n"
        f"- Makro: **{scores['macro']:.2f}**\n"
        f"- Geo: **{scores['geo']:.2f}**\n"
        f"- Governance: **{scores['governance']:.2f}**\n"
        f"- Tech: **{scores['tech']:.2f}**\n"
        f"- Energie: **{scores['energie']:.2f}**\n"
        f"- Währung: **{scores['currency']:.2f}**\n"
        f"- Politische Sicherheit: **{scores['political_security']:.2f}**\n"
    )

    risk_fig = plot_risk_radar(scores)

    return kpi_text, risk_fig

# ------------------------------------------------------------
# HEATMAP-UI
# ------------------------------------------------------------

def ui_heatmap():
    table = risk_heatmap(presets)
    rows = []
    for row in table:
        rows.append([
            row["land"],
            row["macro"], row["macro_color"],
            row["geo"], row["geo_color"],
            row["gov"], row["gov_color"],
            row["currency"], row["currency_color"],
            row["political_security"], row["political_security_color"],
            row["total"], row["total_color"],
        ])
    return rows

# ------------------------------------------------------------
# SZENARIO-DASHBOARD RUN
# ------------------------------------------------------------

def run_scenario(
    country,
    oil_intensity,
    usd_intensity,
    sanc_intensity,
    supply_intensity,
    energy_intensity,
    bank_intensity,
    cyber_intensity,
    dollar_intensity,
    swift_intensity,
    ):

    base_vec = ensure_full_risk_vector(presets[country])
    scores_base = compute_risk_scores(base_vec)

    shock_config = {
        "Ölpreis-Schock": oil_intensity,
        "USD-Zinsanstieg": usd_intensity,
        "Sanktionen": sanc_intensity,
        "Lieferketten-Blockade": supply_intensity,
        "Energieembargo": energy_intensity,
        "Bankenkrise": bank_intensity,
        "Cyberangriff": cyber_intensity,
        "Dollar-Schock": dollar_intensity,
        "SWIFT-Ausschluss": swift_intensity,
    }

    any_shock = any(v and v > 0 for v in shock_config.values())

    ews_base_md = ews_from_scores(scores_base, title=f"Frühwarnsystem – Baseline ({country})")

    if not any_shock:
        fig = plot_risk_radar(scores_base)
        md = (
            f"### ℹ️ Kein aktiver Schock\n"
            f"Es wird nur das Baseline-Risiko für **{country}** angezeigt.\n\n"
            f"**Gesamt-Risiko:** {scores_base['total']:.2f}"
        )
        report = scenario_report(country, scores_base, scores_base, {})
        ews_scen_md = ews_from_scores(scores_base, title=f"Frühwarnsystem – Szenario ({country})")
        return fig, md, report, ews_base_md, ews_scen_md

    scen_vec = apply_multiple_shocks_for_country(country, shock_config)
    scores_scen = compute_risk_scores(scen_vec)

    fig = plot_scenario_compare_radar(scores_base, scores_scen)
    md = scenario_summary(scores_base, scores_scen, shock_config)
    report = scenario_report(country, scores_base, scores_scen, shock_config)
    ews_scen_md = ews_from_scores(scores_scen, title=f"Frühwarnsystem – Szenario ({country})")

    return fig, md, report, ews_base_md, ews_scen_md

# ------------------------------------------------------------
# GRADIO-APP
# ------------------------------------------------------------

def build_app():

    with gr.Blocks() as demo:

        gr.Markdown("# Makro-Risiko-Dashboard")
        gr.Markdown(
            "Dieses Dashboard bündelt Simulation, Radar-Analysen, Heatmaps, "
            "Clusteranalysen und Länderprofile in einer Oberfläche."
        )

        # Dashboard
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

        # Simulation & Radar
        with gr.Tab("Simulation & Radar"):
            gr.Markdown("## Simulation & Radar-Analysen")
            gr.Markdown(
                "Dieser Bereich bietet Risiko-Radare für einzelne Länder, "
                "Vergleiche zwischen zwei Ländern, Multi-Radare und Delta-Analysen."
            )

            sim_country = gr.Dropdown(list(presets.keys()), label="Land auswählen", value=list(presets.keys())[0])
            with gr.Accordion("📊 Risiko‑Radar (Einzelland)", open=False):
                sim_risk_button = gr.Button("📊 Risiko‑Radar anzeigen", variant="primary")
                sim_risk_output = gr.Plot()

                sim_risk_button.click(
                    lambda land: plot_risk_radar(compute_risk_scores(ensure_full_risk_vector(presets[land]))),
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

        # Heatmaps & Cluster
        with gr.Tab("Heatmaps"):

            gr.Markdown("### 1) Standard-Risiko-Heatmap")

            heat_button = gr.Button("Heatmap erzeugen")
            heat_output = gr.Dataframe(
                headers=[
                    "Land",
                    "Makro", "Makro-Farbe",
                    "Geo", "Geo-Farbe",
                    "Gov", "Gov-Farbe",
                    "Währung", "Währungs-Farbe",
                    "Politische Sicherheit", "PS-Farbe",
                    "Total", "Total-Farbe",
                ],
                wrap=True,
                label="Standard-Risiko-Heatmap",
            )

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

        # Risiko-Profil & Frühwarnsystem
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

        # Szenarien & Analyse
        with gr.Tab("Szenarien & Analyse"):
            gr.Markdown("## 🔮 Szenarien, Benchmarking, Heatmap & Storyline 2.0")
            country_sel = gr.Dropdown(list(presets.keys()), label="Land", value=list(presets.keys())[0])

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

            with gr.Accordion("🌍 Benchmarking", open=False):
                bench_btn = gr.Button("Benchmarking anzeigen")
                bench_out = gr.Markdown()

                bench_btn.click(
                    lambda: benchmarking_table(),
                    inputs=None,
                    outputs=bench_out
                )

            with gr.Accordion("🔥 Risiko-Heatmap", open=False):
                heat_btn = gr.Button("Heatmap anzeigen")
                heat_out = gr.Plot()

                heat_btn.click(
                    lambda: plot_heatmap(),
                    inputs=None,
                    outputs=heat_out
                )

            with gr.Accordion("🧠 Storyline 2.0", open=False):
                story_btn = gr.Button("Storyline generieren")
                story_out = gr.Markdown()

                story_btn.click(
                    storyline_v2,
                    inputs=[country_sel],
                    outputs=story_out
                )

        # Szenario-Dashboard
        with gr.Tab("Szenario-Dashboard"):
            gr.Markdown("## 🔮 Szenario-Dashboard")
            gr.Markdown(
                "Kombiniere mehrere Schocks, steuere ihre Intensität und vergleiche Baseline- mit Szenario-Risiko."
            )

            country = gr.Dropdown(
                list(presets.keys()),
                label="Land",
                value=list(presets.keys())[0],
            )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🔧 Schocks & Intensitäten")

                    preset_dropdown = gr.Dropdown(
                        list(scenario_presets.keys()),
                        label="Szenario-Preset auswählen",
                        value=None,
                    )
                    load_preset_btn = gr.Button("Preset laden")

                    oil_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Ölpreis-Schock")
                    usd_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="USD-Zinsanstieg")
                    sanc_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Sanktionen")
                    supply_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Lieferketten-Blockade")
                    energy_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Energieembargo")
                    bank_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Bankenkrise")
                    cyber_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Cyberangriff")
                    dollar_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="Dollar-Schock")
                    swift_intensity = gr.Slider(0.0, 1.0, value=0.0, step=0.1, label="SWIFT-Ausschluss")

                    run_btn = gr.Button("Szenario berechnen", variant="primary")

                with gr.Column():
                    radar_out = gr.Plot(label="Baseline vs. Szenario (Radar)")
                    summary_out = gr.Markdown(label="Kurz-Auswertung")
                    report_out = gr.Markdown(label="Szenario-Report")

            with gr.Row():
                with gr.Column():
                    ews_base_out = gr.Markdown(label="Frühwarnsystem – Baseline")
                with gr.Column():
                    ews_scen_out = gr.Markdown(label="Frühwarnsystem – Szenario")

            load_preset_btn.click(
                fn=lambda name: load_scenario_preset(name),
                inputs=[preset_dropdown],
                outputs=[
                    oil_intensity,
                    usd_intensity,
                    sanc_intensity,
                    supply_intensity,
                    energy_intensity,
                    bank_intensity,
                    cyber_intensity,
                    dollar_intensity,
                    swift_intensity,
                ],
            )

            run_btn.click(
                run_scenario,
                inputs=[
                    country,
                    oil_intensity,
                    usd_intensity,
                    sanc_intensity,
                    supply_intensity,
                    energy_intensity,
                    bank_intensity,
                    cyber_intensity,
                    dollar_intensity,
                    swift_intensity,
                ],
                outputs=[radar_out, summary_out, report_out, ews_base_out, ews_scen_out],
            )

        # Decision Support
        with gr.Tab("Decision Support"):
            gr.Markdown("## 🧭 Decision Support")
            gr.Markdown(
                "Profil, Frühwarnsystem, Szenario und Benchmarking in einem integrierten Blick."
            )

            country = gr.Dropdown(
                list(presets.keys()),
                label="Land",
                value=list(presets.keys())[0],
            )

            with gr.Accordion("Szenario-Einstellungen", open=True):
                oil_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Ölpreis-Schock")
                usd_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="USD-Zinsanstieg")
                sanc_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Sanktionen")
                supply_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Lieferketten-Blockade")
                energy_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Energieembargo")
                bank_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Bankenkrise")
                cyber_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Cyberangriff")
                dollar_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="Dollar-Schock")
                swift_intensity = gr.Slider(0.0, 1.0, 0.0, 0.1, label="SWIFT-Ausschluss")

                run_btn = gr.Button("Decision-Support aktualisieren", variant="primary")

            with gr.Row():
                radar_out = gr.Plot(label="Baseline vs. Szenario (Radar)")
                rec_out = gr.Markdown(label="Kurzinterpretation")

            with gr.Row():
                ews_base_out = gr.Markdown(label="Frühwarnsystem – Baseline")
                ews_scen_out = gr.Markdown(label="Frühwarnsystem – Szenario")

            delta_ews_out = gr.Markdown(label="Delta-EWS")
            scen_report_out = gr.Markdown(label="Szenario-Report")
            bench_out = gr.Markdown(label="Benchmarking")

            run_btn.click(
                decision_support_view,
                inputs=[
                    country,
                    oil_intensity,
                    usd_intensity,
                    sanc_intensity,
                    supply_intensity,
                    energy_intensity,
                    bank_intensity,
                    cyber_intensity,
                    dollar_intensity,
                    swift_intensity,
                ],
                outputs=[
                    radar_out,
                    ews_base_out,
                    ews_scen_out,
                    delta_ews_out,
                    scen_report_out,
                    bench_out,
                    rec_out,
                ],
            )

            with gr.Tab("Autonomie-Heatmap"):
                auto_btn = gr.Button("Autonomie-Heatmap anzeigen")
                auto_out = gr.Dataframe(headers=["Land", "Autonomie", "Ampel"])

                auto_btn.click(lambda: autonomy_heatmap(presets), None, auto_out)

            with gr.Accordion("Szenario-Ranking (Einzelschocks)", open=False):
                rank_intensity = gr.Slider(0.1, 1.0, 1.0, 0.1, label="Test-Intensität für Ranking")
                rank_btn = gr.Button("Ranking berechnen")
                rank_out = gr.Markdown(label="Szenario-Ranking")

                rank_btn.click(
                    scenario_ranking,
                    inputs=[country, rank_intensity],
                    outputs=[rank_out],
                )

        # Länderprofil
        with gr.Tab("Länderprofil"):
            gr.Markdown("## Automatisches Länderprofil")

            country_select = gr.Dropdown(
                list(presets.keys()),
                label="Land auswählen"
            )

            profile_button = gr.Button("Profil erzeugen")
            profile_output = gr.Markdown()

            def ui_country_profile(land):
                base_vec = ensure_full_risk_vector(presets[land])
                scores = compute_risk_scores(base_vec)
                interpretation = interpret_country(scores)
                profile = generate_country_profile(land, presets)
                return f"{profile}\n\n---\n\n### Interpretation\n{interpretation}"

            profile_button.click(
                fn=ui_country_profile,
                inputs=[country_select],
                outputs=profile_output
            )

        # Methodik
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
