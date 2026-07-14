import pandas as pd

def compute_metrics(series: pd.Series) -> dict:
    """
    Einfache Kennzahlen für analyze_ticker.
    Du kannst das später erweitern.
    """
    series = pd.to_numeric(series, errors="coerce").dropna()

    if series.empty:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
        }

    return {
        "count": int(series.count()),
        "mean": float(series.mean()),
        "std": float(series.std()),
        "min": float(series.min()),
        "max": float(series.max()),
    }
