# core/backend/portfolio_optimizer.py

import numpy as np
import pandas as pd
from core.data.assets import fetch_price_history
from core.data.logging import logger

def load_returns(symbols):
    frames = []
    for s in symbols:
        series = fetch_price_history(s)
        if series is None:
            continue
        frames.append(series.pct_change().rename(s))
    if not frames:
        return None
    return pd.concat(frames, axis=1).dropna()


def optimize_markowitz(symbols):
    returns = load_returns(symbols)
    if returns is None:
        return None

    mu = returns.mean() * 252
    cov = returns.cov() * 252
    n = len(symbols)

    w = np.ones(n) / n
    inv_cov = np.linalg.inv(cov)
    w = inv_cov @ mu
    w = w / w.sum()

    return pd.DataFrame({"symbol": symbols, "weight": w})


def optimize_risk_parity(symbols):
    returns = load_returns(symbols)
    if returns is None:
        return None

    cov = returns.cov() * 252
    inv_vol = 1 / np.sqrt(np.diag(cov))
    w = inv_vol / inv_vol.sum()

    return pd.DataFrame({"symbol": symbols, "weight": w})


def optimize_ki_score(df):
    w = df["ki_score"].clip(lower=0)
    if w.sum() == 0:
        w = np.ones(len(df))
    w = w / w.sum()
    return pd.DataFrame({"symbol": df["symbol"], "weight": w})
