# core/scenario_engine.py

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Risiko-Szenarien (für Radar, Storyline, Ampel)
# ---------------------------------------------------------

RISK_SCENARIOS = {
    "Krise": {
        "macro": 0.4,
        "geo": 0.3,
        "financial": 0.5,
        "energie": 0.6,
        "supply_chain": 0.4,
    },
    "Zinsanstieg": {
        "macro": 0.3,
        "financial": 0.6,
        "currency": 0.5,
    },
    "Ölpreisschock": {
        "energie": 0.9,
        "macro": 0.2,
        "supply_chain": 0.3,
    },
    "Keins": {}
}




# ---------------------------------------------------------
# Szenario-Dispatcher
# ---------------------------------------------------------


def apply_risk_scenario(base_scores, scenario_name):
    """
    Wendet ein Risiko-Szenario direkt auf die Risiko-Scores an.
    """
    scenario = RISK_SCENARIOS.get(scenario_name, {})
    new_scores = {}

    for key, value in base_scores.items():
        if isinstance(value, (int, float)):
            shock = scenario.get(key, 0.0)
            new_scores[key] = max(0.0, min(1.0, value + shock))
        else:
            new_scores[key] = value

    return new_scores

def scenario_by_name(name: str):
    """
    Gibt eine Funktion zurück, die Risiko-Scores transformiert.
    """
    def scenario_fn(base_scores):
        return apply_risk_scenario(base_scores, name)
    return scenario_fn


def scenario_radar_overlay(base_scores):
    """
    Liefert ein Dict: {szenario_name: risk_scores_dict}
    für Radar-Overlay.
    """
    out = {}
    for scen in RISK_SCENARIOS.keys():
        scen_fn = scenario_by_name(scen)
        out[scen] = scen_fn(base_scores)
    return out
    
