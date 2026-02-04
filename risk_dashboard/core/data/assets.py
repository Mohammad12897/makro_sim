#core/data/assets.py

import yfinance as yf
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# Hilfsfunktion: Wert in float umwandeln
# ---------------------------------------------------------

def to_float(x):
    """Konvertiert Series/Array/Scalar in float oder None."""
    if x is None:
        return None
    if isinstance(x, (list, tuple, np.ndarray)):
        return float(x[0])
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    try:
        return float(x)
    except:
        return None


# ---------------------------------------------------------
# Kursdaten laden
# ---------------------------------------------------------

def fetch_price_history(symbol, period="5y"):
    try:
        data = yf.download(symbol, period=period, progress=False)
        if data.empty:
            return None
        return data["Close"]
    except:
        return None


# ---------------------------------------------------------
# Kennzahlen
# ---------------------------------------------------------

def calc_return(series, days):
    if len(series) < days:
        return None
    return float((series.iloc[-1] / series.iloc[-days] - 1) * 100)


def calc_volatility(series, days):
    if len(series) < days:
        return None
    vol = series.pct_change().tail(days).std() * np.sqrt(252) * 100
    return to_float(vol)


def calc_sharpe(series, risk_free_rate=0.02):
    daily = series.pct_change().dropna()
    if daily.empty:
        return None

    if isinstance(daily, pd.DataFrame):
        daily = daily.iloc[:, 0]

    excess = daily.mean() * 252 - risk_free_rate
    vol = daily.std() * np.sqrt(252)

    vol = to_float(vol)
    if vol is None or vol == 0:
        return None

    return float(excess / vol)


def calc_drawdown(series):
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return float(drawdown.min() * 100)


def calc_sma_ratio(series, short=50, long=200):
    if len(series) < long:
        return None
    sma_short = series.rolling(short).mean().iloc[-1]
    sma_long = series.rolling(long).mean().iloc[-1]
    return to_float(sma_short / sma_long)


def calc_correlation(series, benchmark_symbol):
    bench = fetch_price_history(benchmark_symbol)
    if bench is None:
        return None
    df = pd.concat([series.pct_change(), bench.pct_change()], axis=1).dropna()
    if df.empty:
        return None
    return float(df.corr().iloc[0, 1])


# ---------------------------------------------------------
# Bitcoin-Kennzahlen
# ---------------------------------------------------------

def get_bitcoin_metrics():
    series = fetch_price_history("BTC-USD")
    if series is None:
        return None

    return {
        "symbol": "BTC-USD",
        "performance_1y": to_float(calc_return(series, 252)),
        "performance_3y": to_float(calc_return(series, 252 * 3)),
        "volatility_90d": to_float(calc_volatility(series, 90)),
        "sharpe": to_float(calc_sharpe(series)),
        "max_drawdown": to_float(calc_drawdown(series)),
        "trend_sma_ratio": to_float(calc_sma_ratio(series, 50, 200)),
        "correlation_spy": to_float(calc_correlation(series, "SPY")),
        "correlation_gold": to_float(calc_correlation(series, "GLD")),
    }


# ---------------------------------------------------------
# Allgemeine Asset-Kennzahlen
# ---------------------------------------------------------

def get_asset_metrics(symbol):
    series = fetch_price_history(symbol)
    if series is None:
        return None

    return {
        "symbol": symbol,
        "performance_1y": to_float(calc_return(series, 252)),
        "performance_3y": to_float(calc_return(series, 252 * 3)),
        "volatility_90d": to_float(calc_volatility(series, 90)),
        "sharpe": to_float(calc_sharpe(series)),
        "max_drawdown": to_float(calc_drawdown(series)),
        "trend_sma_ratio": to_float(calc_sma_ratio(series, 50, 200)),
    }

