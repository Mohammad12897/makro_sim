#core/portfolio_sim/scenario_compare.py
import pandas as pd
from core.portfolio_sim.mc_engine import run_portfolio_mc
from core.portfolio_sim.risk_metrics import mc_risk_metrics


def compare_scenarios(land, presets, weights, years, scenarios):
    results = {}

    for scen in scenarios:
        sim, summary = run_portfolio_mc(
            land=land,
            presets=presets,
            w_equity=weights[0],
            w_bond=weights[1],
            w_gold=weights[2],
            years=years,
            scenario_name=scen
        )
        metrics = mc_risk_metrics(sim)
        results[scen] = metrics

    return results


def run_scenario_comparison(land, presets, weights, years):
    scenarios = ["Keins", "Krise", "Zinsanstieg", "Ölpreisschock"]
    rows = []

    for scen in scenarios:
        sim, summary = run_portfolio_mc(
            land=land,
            presets=presets,
            w_equity=weights[0],
            w_bond=weights[1],
            w_gold=weights[2],
            years=years,
            scenario_name=scen
        )

        m = mc_risk_metrics(sim)

        rows.append([
            scen,
            m["mean"],
            m["std"],
            m["sharpe"],
            m["var95"],
            m["cvar95"],
            m["max_drawdown"]
        ])

    df = pd.DataFrame(rows, columns=[
        "Szenario", "Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])

    return df
