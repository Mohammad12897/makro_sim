#core/portfolio_sim/risk_metricks.py
import numpy as np

def mc_risk_metrics(sim):
    terminal = sim["terminal_distribution"]

    mean = terminal.mean()
    std = terminal.std()
    var95 = np.percentile(terminal, 5)
    cvar95 = terminal[terminal <= var95].mean()
    sharpe = mean / std if std > 0 else float("nan")

    paths = sim["paths"]
    peak = np.maximum.accumulate(paths, axis=1)
    dd = (peak - paths) / peak
    max_dd = dd.max(axis=1).mean()

    return {
        "mean": mean,
        "std": std,
        "sharpe": sharpe,
        "var95": var95,
        "cvar95": cvar95,
        "max_drawdown": max_dd,
    }
