# core/backend/portfolio_backtest.py
import pandas as pd
from core.data.assets import fetch_price_history

def backtest_portfolio(symbols: list[str], weights: list[float], period="5y"):
    frames = []
    for s in symbols:
        series = fetch_price_history(s, period=period)
        if series is None:
            continue
        frames.append(series.rename(s))

    if not frames:
        return None

    prices = pd.concat(frames, axis=1).dropna()
    norm = prices / prices.iloc[0]

    w = pd.Series(weights, index=symbols).reindex(norm.columns).fillna(0)

    portfolio = (norm * w).sum(axis=1)  # Series mit DatetimeIndex

    return portfolio  # Series
