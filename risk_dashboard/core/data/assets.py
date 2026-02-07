# core/data/assets.py
import pandas as pd
import numpy as np
import yfinance as yf
from .caching import cached_download
from .logging import logger

def to_float(x):
    if x is None:
        return None
    if isinstance(x, (list, tuple, np.ndarray)):
        x = x[0]
    if isinstance(x, pd.Series):
        x = x.iloc[0]
    try:
        return float(x)
    except Exception:
        return None

def sanitize_price_data(data):
    """
    Nimmt beliebige yfinance-Rückgaben (DataFrame/Series/MultiIndex)
    und gibt eine saubere Series mit Preisen zurück.
    """
    if data is None or len(data) == 0:
        return None

    # MultiIndex-Case (z.B. Columns: ('Adj Close', 'GLD'))
    if isinstance(data, pd.DataFrame) and isinstance(data.columns, pd.MultiIndex):
        # Versuche 'Adj Close' oder 'Close'
        for lvl0 in ["Adj Close", "Close"]:
            if lvl0 in data.columns.get_level_values(0):
                sub = data[lvl0]
                if isinstance(sub, pd.DataFrame):
                    # erste Spalte nehmen
                    return sub.iloc[:, 0]
                if isinstance(sub, pd.Series):
                    return sub
        # Fallback: erste Spalte
        return data.iloc[:, 0]

    # Normaler DataFrame
    if isinstance(data, pd.DataFrame):
        if "Adj Close" in data.columns:
            return data["Adj Close"]
        if "Close" in data.columns:
            return data["Close"]
        # Fallback: erste Spalte
        return data.iloc[:, 0]

    # Series
    if isinstance(data, pd.Series):
        return data

    return None

def fetch_price_history(symbol, period="5y"):
    try:
        logger.info(f"Downloading data for {symbol}, period={period}")
        raw = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        series = sanitize_price_data(raw)
        if series is None or series.empty:
            logger.warning(f"Empty or invalid data for {symbol}")
            return None
        return series
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None

def calc_return(series, days):
    if len(series) < days:
        return None
    value = (series.iloc[-1] / series.iloc[-days] - 1) * 100
    return to_float(value)

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
    if not vol or vol == 0:
        return None
    return to_float(excess / vol)

def calc_drawdown(series):
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return to_float(drawdown.min() * 100)

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
    return to_float(df.corr().iloc[0, 1])

def safe_rename(series_or_df, name):
    """
    Benennt eine Series oder einen DataFrame zuverlässig in 'name' um.
    Wird genutzt für Heatmap & Optimizer.
    """
    if isinstance(series_or_df, pd.Series):
        return series_or_df.rename(name)
    if isinstance(series_or_df, pd.DataFrame):
        col = series_or_df.columns[0]
        return series_or_df[col].rename(name)
    return None

def get_bitcoin_metrics():
    series = fetch_price_history("BTC-USD")
    if series is None:
        return None
    return {
        "symbol": "BTC-USD",
        "performance_1y": calc_return(series, 252),
        "performance_3y": calc_return(series, 252 * 3),
        "volatility_90d": calc_volatility(series, 90),
        "sharpe": calc_sharpe(series),
        "max_drawdown": calc_drawdown(series),
        "trend_sma_ratio": calc_sma_ratio(series, 50, 200),
        "correlation_spy": calc_correlation(series, "SPY"),
        "correlation_gold": calc_correlation(series, "GLD"),
    }

def get_asset_metrics(symbol):
    series = fetch_price_history(symbol)
    if series is None:
        return None
    return {
        "symbol": symbol,
        "performance_1y": calc_return(series, 252),
        "performance_3y": calc_return(series, 252 * 3),
        "volatility_90d": calc_volatility(series, 90),
        "sharpe": calc_sharpe(series),
        "max_drawdown": calc_drawdown(series),
        "trend_sma_ratio": calc_sma_ratio(series, 50, 200),
    }
