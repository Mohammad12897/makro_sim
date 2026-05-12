#core/analysis/portfolio_metrics.py
def aggregate_portfolio(rows, weights):
    agg = {"Ticker": "Portfolio"}
    keys = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]

    for k in keys:
        vals = []
        for r, w in zip(rows, weights):
            v = r.get(k)
            if v is not None:
                vals.append(w * float(v))
        agg[k] = sum(vals) if vals else None

    return agg
