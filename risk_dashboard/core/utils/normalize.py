#core/utils/normalize.py
import copy
import math

def normalize_metrics_list(rows, scope: str):
    """
    rows: Liste von Dicts
    scope: "aktien", "laender", "etf", "portfolio"
    erzeugt für jede Kennzahl einen normierten Wert: key + " norm"
    """

    rows = copy.deepcopy(rows)

    # Kennzahlen pro Scope
    metric_sets = {
        "aktien": [
            "1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta",
            "KGV", "KBV", "KUV", "DivRendite %",
            "BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote",
        ],
        "laender": [
            "BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote",
        ],
        "etf": [
            "1Y %", "5Y %", "Volatilität %", "Sharpe",
            "TER", "Tracking Error", "AUM", "DivRendite %",
        ],
        "portfolio": [
            "Gewichteter Sharpe", "Gewichtete Volatilität",
            "1Y %", "5Y %",
        ],
    }

    metrics = metric_sets.get(scope, [])

    # Min/Max sammeln
    mins = {m: math.inf for m in metrics}
    maxs = {m: -math.inf for m in metrics}

    for r in rows:
        for m in metrics:
            v = r.get(m)
            if v is None:
                continue
            try:
                v = float(v)
            except Exception:
                continue
            mins[m] = min(mins[m], v)
            maxs[m] = max(maxs[m], v)

    # Normierung 0–1
    for r in rows:
        for m in metrics:
            v = r.get(m)
            if v is None:
                r[m + " norm"] = 0.0
                continue
            try:
                v = float(v)
            except Exception:
                r[m + " norm"] = 0.0
                continue

            mn, mx = mins[m], maxs[m]
            if mx == mn:
                r[m + " norm"] = 0.5
            else:
                r[m + " norm"] = (v - mn) / (mx - mn)

    return rows
