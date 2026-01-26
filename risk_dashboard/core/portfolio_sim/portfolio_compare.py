#core/portfolio_sim/portfolio_compare.py
import pandas as pd
from core.portfolio_sim.mc_engine import run_portfolio_mc
from core.portfolio_sim.risk_metrics import mc_risk_metrics

def compare_portfolios(land, presets, portfolios, years, scenario):
    rows = []

    for name, weights in portfolios.items():
        sim, summary = run_portfolio_mc(
            land=land,
            presets=presets,
            w_equity=weights[0],
            w_bond=weights[1],
            w_gold=weights[2],
            years=years,
            scenario_name=scenario
        )

        m = mc_risk_metrics(sim)

        rows.append([name, m["mean"], m["std"], m["sharpe"], m["var95"], m["cvar95"], m["max_drawdown"]])

    df = pd.DataFrame(rows, columns=[
        "Portfolio", "Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])

    return df
