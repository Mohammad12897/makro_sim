# core/data/market_data.py

import yfinance as yf
import pandas as pd
import numpy as np


def load_asset_series(ticker: str, start="2010-01-01", end=None):
    data = yf.download(ticker, start=start, end=end, progress=False)

    if data.empty:
        raise ValueError(f"Keine Daten für {ticker}")

    prices = data["Adj Close"].dropna()
    returns = prices.pct_change().dropna()

    return {
        "ticker": ticker,
        "dates": prices.index,
        "prices": prices.values,
        "returns": returns.values,
    }

def get_etf(ticker):
    return load_asset_series(ticker)

def get_gold():
    return load_asset_series("GC=F")  # Gold-Future

def get_bond():
    return load_asset_series("IEF")  # US 7-10y Treasury ETF

