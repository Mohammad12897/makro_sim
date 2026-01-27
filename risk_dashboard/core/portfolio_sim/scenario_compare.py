# core/portfolio_sim/scenario_compare.py
# MC-freier Szenario-Vergleich (Option A)

from core.scenario_engine import apply_risk_scenario, RISK_SCENARIOS

def run_scenario_comparison(country, base_scores, weights, years):
    """
    Vergleicht Risiko-Szenarien ohne Portfolio-Simulation.
    Gibt ein Dict zurück: {szenario_name: risk_scores_dict}
    """
    results = {}

    for scen_name in RISK_SCENARIOS.keys():
        shocked = apply_risk_scenario(base_scores, scen_name)
        results[scen_name] = shocked

    return results
