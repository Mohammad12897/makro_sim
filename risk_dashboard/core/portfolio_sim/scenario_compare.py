#core/portfolio_sim/scenario_compare.py
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

def run_scenario_comparison(land, w_equity, w_bond, w_gold, years):
    presets = load_presets()
    scenarios = ["Keins", "Krise", "Zinsanstieg", "Ölpreisschock"]

    results = compare_scenarios(
        land=land,
        presets=presets,
        weights=[w_equity, w_bond, w_gold],
        years=years,
        scenarios=scenarios
    )

    # Tabelle bauen
    rows = []
    for scen, m in results.items():
        rows.append([
            scen,
            f"{m['mean']*100:.2f}%",
            f"{m['std']*100:.2f}%",
            f"{m['sharpe']:.2f}",
            f"{m['var95']*100:.2f}%",
            f"{m['cvar95']*100:.2f}%",
            f"{m['max_drawdown']*100:.2f}%"
        ])

    df = pd.DataFrame(rows, columns=[
        "Szenario", "Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])

    return df
