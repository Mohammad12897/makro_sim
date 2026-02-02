#core/analysis/normalize.py
def normalize_metrics(rows):
    # Alle Kennzahlen, die normiert werden sollen
    metrics = [
        "1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta",
        "KGV", "KBV", "KUV", "DivRendite %"
    ]

    # Fehlende Werte ersetzen
    for r in rows:
        for m in metrics:
            if r.get(m) is None:
                r[m] = 0

    # Min/Max bestimmen
    mins = {m: min(r[m] for r in rows) for m in metrics}
    maxs = {m: max(r[m] for r in rows) for m in metrics}

    # Normierung
    for r in rows:
        for m in metrics:
            lo = mins[m]
            hi = maxs[m]
            val = r[m]

            if hi == lo:
                r[m + " norm"] = 0.5
            else:
                r[m + " norm"] = (val - lo) / (hi - lo)

    return rows
