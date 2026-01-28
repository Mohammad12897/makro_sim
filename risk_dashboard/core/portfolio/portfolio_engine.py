#core/portfolio/portfolio_engine.py

import numpy as np
import pandas as pd


def simulate_portfolio(asset_data: dict, weights: dict):
    dfs = []

    for ticker, data in asset_data.items():
        df = pd.DataFrame({
            ticker: np.array(data["returns"]).reshape(-1)
        }, index=data["dates"])

        dfs.append(df)

    # Zeitreihen exakt nach Datum ausrichten
    merged = pd.concat(dfs, axis=1, join="inner").dropna()

    w = np.array([weights[t] for t in merged.columns])
    merged["portfolio"] = merged.values @ w

    return merged

def portfolio_performance(series):
    return (1 + series).cumprod() - 1


def portfolio_volatility(series):
    return series.std() * np.sqrt(252)


def max_drawdown(series):
    cum = (1 + series).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return dd.min()


def portfolio_stats(series):
    return {
        "Volatilität": portfolio_volatility(series),
        "Max Drawdown": max_drawdown(series),
        "Gesamtrendite": series.add(1).prod() - 1,
    }
