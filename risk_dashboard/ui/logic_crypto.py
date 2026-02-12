import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def ui_crypto_analysis(ticker):
    series = fetch_price_history(ticker, period="1y")

    if not isinstance(series, pd.Series) or len(series) < 120:
        return pd.DataFrame([["Keine Daten"]], columns=["Info"]), None

    result = compute_ki_score(series, return_factors=True)

    if not isinstance(result, tuple) or len(result) != 2:
        return pd.DataFrame([["KI‑Score Fehler"]]), None

    score, factors = result

    if not isinstance(factors, dict):
        return pd.DataFrame([["Faktoren ungültig"]]), None

    fig = plot_radar({ticker: factors})

    returns = series.pct_change().dropna()
    df = pd.DataFrame({
        "Kennzahl": ["Volatilität", "Sharpe‑Ratio"],
        "Wert": [
            returns.std() * (252 ** 0.5),
            returns.mean() / (returns.std() + 1e-9)
        ]
    })

    return df, fig
