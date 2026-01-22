# core/scenario_engine.py

from __future__ import annotations
from typing import Dict, List
from copy import deepcopy

from core.risk_model import compute_risk_scores, clamp01
from core.shock_mapping import convert_events_to_shocks

import json

# ---------------------------------------------------------
# Hilfsfunktion: sichere Addition mit Begrenzung
# ---------------------------------------------------------
def load_lexicon() -> dict:
    with open("data/lexicon.json", "r") as f:
        return json.load(f)


def add_risk(value: float, delta: float) -> float:
    """
    Erhöht oder senkt einen Risiko-Parameter und begrenzt ihn auf [0,1].
    """
    return clamp01(value + delta)


# ---------------------------------------------------------
# Shock-Definitionen
# ---------------------------------------------------------

def apply_shock(params: dict, shock_type: str, intensity: float = 1.0) -> dict:
    """
    Wendet einen einzelnen Schock auf die Parameter an.
    intensity = 1.0 entspricht 100% des Schockeffekts.
    """
    p = deepcopy(params)
    f = intensity

    # -----------------------------
    # Energie-Schocks
    # -----------------------------
    if shock_type == "Ölpreis +50%":
        p["energie"] = add_risk(p.get("energie", 0.5), 0.25 * f)
        p["import_kritische_gueter"] = add_risk(p.get("import_kritische_gueter", 0.5), 0.15 * f)

    elif shock_type == "Gasembargo":
        p["energie"] = add_risk(p.get("energie", 0.5), 0.35 * f)
        p["chokepoint_abhaengigkeit"] = add_risk(p.get("chokepoint_abhaengigkeit", 0.5), 0.20 * f)

    # -----------------------------
    # Finanz- & Währungsschocks
    # -----------------------------
    elif shock_type == "USD-Zinsanstieg":
        p["kapitalmarkt_abhaengigkeit"] = add_risk(p.get("kapitalmarkt_abhaengigkeit", 0.5), 0.20 * f)
        p["fremdwaehrungs_refinanzierung"] = add_risk(p.get("fremdwaehrungs_refinanzierung", 0.5), 0.15 * f)

    elif shock_type == "Dollar-Schock":
        p["USD_Dominanz"] = add_risk(p.get("USD_Dominanz", 0.5), 0.20 * f)
        p["FX_Schockempfindlichkeit"] = add_risk(p.get("FX_Schockempfindlichkeit", 0.5), 0.20 * f)

    elif shock_type == "SWIFT-Ausschluss":
        p["Sanktions_Exposure"] = add_risk(p.get("Sanktions_Exposure", 0.1), 0.40 * f)
        p["fremdwaehrungs_refinanzierung"] = add_risk(p.get("fremdwaehrungs_refinanzierung", 0.5), 0.25 * f)
        p["aussenpolitische_abhaengigkeit"] = add_risk(p.get("aussenpolitische_abhaengigkeit", 0.5), 0.15 * f)

    # -----------------------------
    # Handels- & Lieferkettenschocks
    # -----------------------------
    elif shock_type == "Lieferketten-Blockade":
        p["chokepoint_abhaengigkeit"] = add_risk(p.get("chokepoint_abhaengigkeit", 0.5), 0.30 * f)
        p["produktions_konzentration"] = add_risk(p.get("produktions_konzentration", 0.5), 0.20 * f)

    elif shock_type == "Exportstopp":
        p["export_konzentration"] = add_risk(p.get("export_konzentration", 0.5), 0.25 * f)
        p["partner_konzentration"] = add_risk(p.get("partner_konzentration", 0.5), 0.20 * f)

    # -----------------------------
    # Politische & sicherheitspolitische Schocks
    # -----------------------------
    elif shock_type == "Sanktionen":
        p["sanktionsverwundbarkeit"] = add_risk(p.get("sanktionsverwundbarkeit", 0.5), 0.30 * f)
        p["aussenpolitische_abhaengigkeit"] = add_risk(p.get("aussenpolitische_abhaengigkeit", 0.5), 0.15 * f)

    elif shock_type == "Geopolitische Spannung":
        p["externer_einfluss"] = add_risk(p.get("externer_einfluss", 0.5), 0.25 * f)
        p["diplomatische_resilienz"] = add_risk(p.get("diplomatische_resilienz", 0.5), -0.20 * f)

    elif shock_type == "Bündnisverlust":
        p["sicherheitsgarantien"] = add_risk(p.get("sicherheitsgarantien", 0.5), -0.40 * f)
        p["externer_einfluss"] = add_risk(p.get("externer_einfluss", 0.5), 0.20 * f)

    # -----------------------------
    # Tech-Schocks
    # -----------------------------
    elif shock_type == "Technologie-Embargo":
        p["halbleiter_abhaengigkeit"] = add_risk(p.get("halbleiter_abhaengigkeit", 0.5), 0.30 * f)
        p["software_cloud_abhaengigkeit"] = add_risk(p.get("software_cloud_abhaengigkeit", 0.5), 0.20 * f)

    elif shock_type == "Cyberangriff":
        p["software_cloud_abhaengigkeit"] = add_risk(p.get("software_cloud_abhaengigkeit", 0.5), 0.25 * f)
        p["schluesseltechnologie_importe"] = add_risk(p.get("schluesseltechnologie_importe", 0.5), 0.15 * f)

    return p


# ---------------------------------------------------------
# Szenario Runner
# ---------------------------------------------------------
def run_scenario(params, shocks):
    """
    shocks = bereits konvertierte Risiko-Shocks (Dict)
    oder eine Event-Liste (List)
    """

    # Falls shocks eine Event-Liste ist → konvertieren
    if isinstance(shocks, list):
        shocks = convert_events_to_shocks(shocks)

    # params kopieren
    modified = params.copy()

    # Risiko-Shocks anwenden
    for dim, delta in shocks.items():
        if dim in modified:
            modified[dim] = min(1.0, modified[dim] + delta)

    return compute_risk_scores(modified)


# ---------------------------------------------------------
# Szenario Ranking
# ---------------------------------------------------------

def rank_countries(presets: dict) -> list:
    """
    Erstellt ein Ranking aller Länder nach Gesamtrisiko.
    Rückgabe: Liste [(Land, Risiko), ...] absteigend sortiert.
    """
    ranking = []
    for country, params in presets.items():
        scores = compute_risk_scores(params)
        ranking.append((country, scores["total"]))

    return sorted(ranking, key=lambda x: x[1], reverse=True)

def rank_scenarios(base_params: dict, scenario_dict: Dict[str, List[Dict]]) -> List[tuple]:
    """
    Berechnet für jedes Szenario das resultierende Gesamtrisiko
    und gibt eine sortierte Liste zurück.
    """
    ranking = []

    for name, events  in scenario_dict.items():
        shock_values = convert_events_to_shocks(events)
        scen_scores = run_scenario(base_params, shock_values)
        scen_total = scen_scores["total"]
        ranking.append((name, scen_total))

    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking

# ---------------------------------------------------------
# Decision Support View
# ---------------------------------------------------------

    
### Automatische Szenario-Interpretation  
def interpret_single_scenario(base_params: dict, scenario_name: str, shocks: list) -> str:
    """
    Erzeugt eine narrative Interpretation eines einzelnen Szenarios.
    """
    base_scores = compute_risk_scores(base_params)
    shock_values = convert_events_to_shocks(shocks)
    scen_scores = run_scenario(base_params, shock_values)

    md = f"# 📉 Szenario-Interpretation – {scenario_name}\n\n"

    md += "## Δ Risiko-Dimensionen\n"
    for dim in ["macro", "geo", "governance", "handel", "supply_chain",
                "financial", "tech", "energie", "currency",
                "political_security", "strategische_autonomie", "total"]:
        before = base_scores[dim]
        after = scen_scores[dim]
        delta = after - before
        if abs(delta) < 0.02:
            continue
        sign = "▲" if delta > 0 else "▼"
        md += f"- **{dim}**: {before:.2f} → {after:.2f} ({sign} {delta:+.2f})\n"

    md += "\n## Kernaussage\n"

    total_delta = scen_scores["total"] - base_scores["total"]
    if total_delta > 0.1:
        md += "- Das Szenario **verschärft die Gesamtrisikolage deutlich**.\n"
    elif total_delta > 0.03:
        md += "- Das Szenario **erhöht das Risiko moderat**.\n"
    elif total_delta > -0.03:
        md += "- Das Szenario verändert die Gesamtrisikolage **nur geringfügig**.\n"
    else:
        md += "- Das Szenario **reduziert die Gesamtrisikolage**.\n"

    md += "\n## Politische Abhängigkeit & Autonomie\n"
    ps_delta = scen_scores["political_security"] - base_scores["political_security"]
    sa_delta = scen_scores["strategische_autonomie"] - base_scores["strategische_autonomie"]

    if ps_delta > 0.05:
        md += "- Die **politische Abhängigkeit nimmt spürbar zu**.\n"
    elif ps_delta < -0.05:
        md += "- Die **politische Abhängigkeit nimmt ab**.\n"

    if sa_delta > 0.05:
        md += "- Die **strategische Autonomie verbessert sich**.\n"
    elif sa_delta < -0.05:
        md += "- Die **strategische Autonomie verschlechtert sich**.\n"

    return md


def interpret_single_scenario_compact(base_params: dict, scenario_name: str, shocks: list) -> str:
    base_scores = compute_risk_scores(base_params)
    shock_values = convert_events_to_shocks(shocks)
    scen_scores = run_scenario(base_params, shock_values)

    md = ""
    for dim in [
        "macro", "geo", "governance", "handel", "supply_chain",
        "financial", "tech", "energie", "currency",
        "political_security", "strategische_autonomie", "total"
    ]:
        before = base_scores[dim]
        after = scen_scores[dim]
        delta = after - before

        if abs(delta) < 0.02:
            continue

        sign = "▲" if delta > 0 else "▼"
        md += f"- **{dim}**: {before:.2f} → {after:.2f} ({sign} {delta:+.2f})\n"

    return md

def interpret_single_scenario_full(base_params: dict, scenario_name: str, shocks: list) -> str:
    base_scores = compute_risk_scores(base_params)
    shock_values = convert_events_to_shocks(shocks)
    scen_scores = run_scenario(base_params, shock_values)

    md = f"# 📉 Szenario-Interpretation – {scenario_name}\n\n"

    md += "## Δ Risiko-Dimensionen\n"
    for dim in [
        "macro", "geo", "governance", "handel", "supply_chain",
        "financial", "tech", "energie", "currency",
        "political_security", "strategische_autonomie", "total"
    ]:
        before = base_scores[dim]
        after = scen_scores[dim]
        delta = after - before
        if abs(delta) < 0.02:
            continue
        sign = "▲" if delta > 0 else "▼"
        md += f"- **{dim}**: {before:.2f} → {after:.2f} ({sign} {delta:+.2f})\n"

    md += "\n## Kernaussage\n"
    total_delta = scen_scores["total"] - base_scores["total"]

    if total_delta > 0.1:
        md += "- Das Szenario **verschärft die Gesamtrisikolage deutlich**.\n"
    elif total_delta > 0.03:
        md += "- Das Szenario **erhöht das Risiko moderat**.\n"
    elif total_delta > -0.03:
        md += "- Das Szenario verändert die Gesamtrisikolage **nur geringfügig**.\n"
    else:
        md += "- Das Szenario **reduziert die Gesamtrisikolage**.\n"

    md += "\n## Politische Abhängigkeit & Autonomie\n"
    ps_delta = scen_scores["political_security"] - base_scores["political_security"]
    sa_delta = scen_scores["strategische_autonomie"] - base_scores["strategische_autonomie"]

    if ps_delta > 0.05:
        md += "- Die **politische Abhängigkeit nimmt spürbar zu**.\n"
    elif ps_delta < -0.05:
        md += "- Die **politische Abhängigkeit nimmt ab**.\n"

    if sa_delta > 0.05:
        md += "- Die **strategische Autonomie verbessert sich**.\n"
    elif sa_delta < -0.05:
        md += "- Die **strategische Autonomie verschlechtert sich**.\n"

    return md

def decision_support_view(base_params: dict, scenario_dict: Dict[str, List[Dict]]) -> str:
    """
    Hybrid-Version:
    - Ranking aller Szenarien
    - Empfehlung (bestes / schlechtestes Szenario)
    - Kompakte technische Interpretation
    - Ausführliche narrative Analyse (optional)
    """
    ranking = rank_scenarios(base_params, scenario_dict)

    md = "# 🧭 Decision Support – Szenarioanalyse\n\n"
    md += "Die Szenarien sind nach Gesamtrisiko sortiert:\n\n"

    # -------------------------
    # Ranking
    # -------------------------
    for name, score in ranking:
        md += f"- **{name}** → Risiko: **{score:.2f}**\n"

    # -------------------------
    # Empfehlung
    # -------------------------
    worst = ranking[0]
    best = ranking[-1]

    md += "\n## Empfehlung\n"
    md += (
        f"- Kritischstes Szenario: **{worst[0]}** (Risiko {worst[1]:.2f})\n"
        f"- Günstigstes Szenario: **{best[0]}** (Risiko {best[1]:.2f})\n"
    )

    # -------------------------
    # Detailanalyse
    # -------------------------
    md += "\n---\n"
    md += "## Detailanalyse\n\n"

    for name, shocks in scenario_dict.items():

        # Kompakte technische Interpretation
        md += f"### 🔹 {name}\n"
        md += interpret_single_scenario_compact(base_params, name, shocks)

        # Ausführliche narrative Interpretation (optional)
        md += "\n<details>\n"
        md += "<summary>📘 Ausführliche Analyse anzeigen</summary>\n\n"
        md += interpret_single_scenario_full(base_params, name, shocks)
        md += "\n</details>\n"
        md += "\n---\n"

    lex = load_lexicon()
    md += "\n---\n## 📘 Lexikon der Risiko-Dimensionen\n\n"
    for key, desc in lex.items():
        md += f"- **{key}**: {desc}\n"
    return md
