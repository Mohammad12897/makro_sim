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

def simulate_portfolio_with_rebalancing(asset_data: dict, weights: dict, freq="M"):
    dfs = []
    for ticker, data in asset_data.items():
        df = pd.DataFrame({ticker: data["returns"]}, index=data["dates"])
        dfs.append(df)

    merged = pd.concat(dfs, axis=1, join="inner").dropna()

    # Rebalancing-Zeitpunkte
    rebal_dates = merged.resample(freq).first().index

    port_ret = []
    current_w = np.array([weights[t] for t in merged.columns])

    for i, (idx, row) in enumerate(merged.iterrows()):
        if idx in rebal_dates:
            current_w = np.array([weights[t] for t in merged.columns])
        port_ret.append(row.values @ current_w)

    merged["portfolio_rebal"] = port_ret
    return merged
    
