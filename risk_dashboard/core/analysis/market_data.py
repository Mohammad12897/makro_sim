# core/analysis/market_data.py
import datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf

def get_history(ticker, years=5):
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * years)
    df = yf.Ticker(ticker).history(start=start, end=end)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    return df["Adj Close"].dropna()

def calc_returns(prices):
    return prices.pct_change().dropna()

def annual_vol(returns):
    return returns.std() * np.sqrt(252)

def sharpe_ratio(returns):
    if returns.empty:
        return np.nan
    vol = annual_vol(returns)
    if vol == 0:
        return np.nan
    return (returns.mean() * 252) / vol

def max_drawdown(prices):
    if prices.empty:
        return np.nan
    roll_max = prices.cummax()
    dd = prices / roll_max - 1
    return dd.min()

def perf(series):
    if series.empty:
        return np.nan
    return float(series.iloc[-1] / series.iloc[0] - 1)

def get_metrics(entry):
    ticker = entry["ticker"]
    name = entry.get("name", ticker)
    region = entry.get("region", "Global")
    asset_class = entry.get("asset_class", "Equity")

    prices = get_history(ticker, years=5)
    if prices.empty:
        return None

    one_year = prices[prices.index >= (prices.index.max() - pd.Timedelta(days=365))]
    rets = calc_returns(prices)

    return {
        "Ticker": ticker,
        "Name": name,
        "Region": region,
        "Asset-Klasse": asset_class,
        "1Y %": round(perf(one_year) * 100, 2),
        "5Y %": round(perf(prices) * 100, 2),
        "Volatilität %": round(annual_vol(rets) * 100, 2),
        "Sharpe": round(sharpe_ratio(rets), 2),
        "Max Drawdown %": round(max_drawdown(prices) * 100, 2),
    }
