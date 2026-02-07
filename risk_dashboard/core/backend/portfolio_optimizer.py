# core/backend/portfolio_optimizer.py

import numpy as np
import pandas as pd
from core.data.assets import fetch_price_history, safe_rename
from core.data.logging import logger

def load_returns(symbols):
    frames = []
    for s in symbols:
        series = fetch_price_history(s)
        if series is None:
            continue
        renamed = safe_rename(series.pct_change(), s)
        if renamed is not None:
            frames.append(renamed)
    if not frames:
        return None
    return pd.concat(frames, axis=1).dropna()

def optimize_markowitz(symbols):
    returns = load_returns(symbols)
    if returns is None or returns.empty:
        logger.warning("No returns data for Markowitz optimization")
        return pd.DataFrame({"Fehler": ["Keine Renditedaten verfügbar"]})

    mu = returns.mean() * 252
    cov = returns.cov() * 252
    n = len(returns.columns)

    try:
        inv_cov = np.linalg.inv(cov.values)
    except Exception:
        logger.warning("Covariance matrix not invertible, using equal weights")
        w = np.ones(n) / n
        return pd.DataFrame({"symbol": returns.columns, "weight": w})

    w = inv_cov @ mu.values
    w = np.maximum(w, 0)  # keine negativen Gewichte
    if w.sum() == 0:
        w = np.ones(n)
    w = w / w.sum()

    return pd.DataFrame({"symbol": returns.columns, "weight": w})

def optimize_risk_parity(symbols):
    returns = load_returns(symbols)
    if returns is None or returns.empty:
        logger.warning("No returns data for risk parity")
        return pd.DataFrame({"Fehler": ["Keine Renditedaten verfügbar"]})

    cov = returns.cov() * 252
    vols = np.sqrt(np.diag(cov.values))
    inv_vol = 1 / vols
    w = inv_vol / inv_vol.sum()

    return pd.DataFrame({"symbol": returns.columns, "weight": w})

def optimize_ki_score(df):
    if df is None or df.empty or "ki_score" not in df.columns:
        return pd.DataFrame({"Fehler": ["Keine KI‑Scores verfügbar"]})
    w = df["ki_score"].clip(lower=0)
    if w.sum() == 0:
        w = np.ones(len(df))
    w = w / w.sum()
    return pd.DataFrame({"symbol": df["symbol"], "weight": w})
