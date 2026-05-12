
# core/portfolio_sim/scenario_compare.py

from core.scenario_engine import apply_risk_scenario, RISK_SCENARIOS

def run_scenario_comparison(country, base_scores, weights, years):
    results = {}
    for scen_name in RISK_SCENARIOS.keys():
        results[scen_name] = apply_risk_scenario(base_scores, scen_name)
    return results
