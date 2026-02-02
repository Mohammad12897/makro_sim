#core/analysis/normalize.py
def normalize_metrics(rows):
    metrics = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]

    # Min/Max pro Kennzahl bestimmen
    mins = {m: min(r.get(m, 0) for r in rows) for m in metrics}
    maxs = {m: max(r.get(m, 0) for r in rows) for m in metrics}

    # Normierung
    for r in rows:
        for m in metrics:
            lo = mins[m]
            hi = maxs[m]
            val = r.get(m, 0)

            if hi == lo:
                r[m + " norm"] = 0.5
            else:
                r[m + " norm"] = (val - lo) / (hi - lo)

    return rows
