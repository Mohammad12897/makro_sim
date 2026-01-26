import numpy as np
import matplotlib.pyplot as plt

from core.scenario_engine import scenario_by_name, dynamic_covariance

def run_portfolio_mc(land, presets, w_equity, w_bond, w_gold, years, scenario_name):

    # PRESETS ENTHALTEN BEREITS ALLE ERWARTUNGEN
    expectations = presets

    mu = {
        "equity": expectations["equity"]["mu"][0],
        "bonds": expectations["bonds"]["mu"][1],
        "gold": expectations["gold"]["mu"][2],
    }

    cov = build_asset_covariance()
    cov = dynamic_covariance(cov, scenario_name)

    weights = [w_equity, w_bond, w_gold]
    weights = [w / sum(weights) for w in weights]

    shock_fn = scenario_by_name(scenario_name)

    sim = multi_period_mc(
        weights=weights,
        mu=mu,
        cov=cov,
        years=years,
        n_paths=3000,
        rebalancing=True,
        shock_fn=shock_fn,
        seed=42,
    )

    summary = summarize_paths(sim)
    return sim, summary
