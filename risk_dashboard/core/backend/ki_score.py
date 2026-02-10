#core/backend/ki_score.py

import numpy as np
import pandas as pd

def normalize(value, min_val, max_val):
    if max_val - min_val == 0:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def compute_ki_score(price_series: pd.Series) -> float:
    """
    Berechnet einen KI-Score (0–100) aus einer Preiszeitreihe.
    """

    # 1. Renditen
    returns = price_series.pct_change().dropna()

    # 2. Momentum (letzte 90 Tage)
    momentum = price_series.iloc[-1] / price_series.iloc[-90] - 1
    momentum_norm = normalize(momentum, -0.2, 0.3)

    # 3. Volatilität
    vol = returns.std()
    vol_norm = normalize(vol, 0.005, 0.05)

    # 4. Sharpe Ratio
    sharpe = returns.mean() / (returns.std() + 1e-9)
    sharpe_norm = normalize(sharpe, -1, 2)

    # 5. Max Drawdown
    roll_max = price_series.cummax()
    drawdown = ((price_series - roll_max) / roll_max).min()
    drawdown_norm = normalize(abs(drawdown), 0, 0.5)

    # 6. Trendstabilität (R² der linearen Regression)
    x = np.arange(len(price_series))
    y = price_series.values
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2)
    trend_stability_norm = normalize(r2, 0, 1)

    # 7. KI-Score
    score = (
        0.25 * momentum_norm +
        0.20 * sharpe_norm +
        0.20 * trend_stability_norm +
        0.20 * (1 - drawdown_norm) +
        0.15 * (1 - vol_norm)
    ) * 100

    return float(np.clip(score, 0, 100))
