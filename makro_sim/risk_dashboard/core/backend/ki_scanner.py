# core/backend/ki_scanner.py
import pandas as pd
from core.data.assets import get_asset_metrics, get_bitcoin_metrics
from core.visualization.radar_plotly_assets import plot_asset_radar

REGIONS = {
    "Europa": ['EUNA.DE', '4GLD.DE', 'EWQ', 'ISF.L', 'CAC.PA', 'VUKE.L', 'CSUK.L'],
    "USA": ['SPY', 'VTI', 'AGG', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA'],
    "Global": ['EUNL.DE', 'EUNA.DE', 'SPY', 'SGLN.L', '4GLD.DE', 'VTI', 'AGG',
               'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'GLD', 'IAU',
               'EWQ', 'ISF.L', 'EWJ', 'CAC.PA', 'VUKE.L', 'CSUK.L', 'SJPA.L', 'XDJP.DE', 'JPN.PA']
}

PROFILES = {
    "ki": {"sharpe": 0.35, "performance_1y": 0.20, "performance_3y": 0.10,
           "trend_sma_ratio": 0.15, "volatility_90d": -0.10, "max_drawdown": -0.10},
    "stabil": {"sharpe": 0.40, "volatility_90d": -0.30, "max_drawdown": -0.20, "trend_sma_ratio": 0.10},
    "momentum": {"trend_sma_ratio": 0.40, "performance_1y": 0.30, "performance_3y": 0.20, "sharpe": 0.10},
    "growth": {"performance_1y": 0.40, "performance_3y": 0.30, "trend_sma_ratio": 0.20, "sharpe": 0.10},
    "diversifikation": {"correlation_spy": -0.40, "correlation_gold": -0.40,
                        "volatility_90d": -0.10, "sharpe": 0.10},
    "krypto": {"trend_sma_ratio": 0.50, "performance_1y": 0.30, "volatility_90d": -0.20},
    "etf": {"performance_3y": 0.30, "sharpe": 0.30, "volatility_90d": -0.20, "max_drawdown": -0.20},
}

def compute_ki_score(df: pd.DataFrame, profile: str) -> pd.DataFrame:
    w = PROFILES.get(profile, PROFILES["ki"])
    df = df.copy()
    df["ki_score"] = 0.0
    for key, weight in w.items():
        if key in df.columns:
            df["ki_score"] += df[key].fillna(0) * weight
    return df

def scan_assets(asset_string: str, profile: str, region: str):

    if region in REGIONS and (not asset_string or asset_string.strip() == ""):
        symbols = REGIONS[region]
    else:
        if not asset_string:
            return pd.DataFrame({"Fehler": ["Keine Assets eingegeben"]}), None
        symbols = [s.strip().upper() for s in asset_string.split(",")]

    rows = []
    for symbol in symbols:
        if symbol == "BTC-USD":
            metrics = get_bitcoin_metrics()
        else:
            metrics = get_asset_metrics(symbol)
        if metrics is not None:
            rows.append(metrics)

    if not rows:
        return pd.DataFrame({"Fehler": ["Keine gültigen Assets gefunden"]}), None

    df = pd.DataFrame(rows)
    df = compute_ki_score(df, profile)
    df = df.sort_values("ki_score", ascending=False)

    fig = plot_asset_radar(rows, mode="experte")

    return df, fig
