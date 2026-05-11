# core/backend/portfolio_radar.py
import pandas as pd
from core.data.assets import get_asset_metrics
from core.visualization.radar_plotly_assets import plot_asset_radar

def build_portfolio_metrics(symbols: list[str], weights: list[float]):
    rows = []
    for s in symbols:
        m = get_asset_metrics(s)
        if m:
            rows.append(m)
    if not rows:
        return None, None

    df = pd.DataFrame(rows)
    w = pd.Series(weights, index=df["symbol"]).reindex(df["symbol"]).fillna(0)
    df["weight"] = w.values

    agg = {}
    for col in ["performance_1y", "performance_3y", "volatility_90d", "sharpe", "max_drawdown", "trend_sma_ratio"]:
        if col in df.columns:
            agg[col] = (df[col] * df["weight"]).sum()

    return df, agg

def portfolio_radar(symbols: list[str], weights: list[float]):
    rows = []
    for s in symbols:
        m = get_asset_metrics(s)
        if m:
            rows.append(m)
    if not rows:
        return None
    return plot_asset_radar(rows, mode="experte")
