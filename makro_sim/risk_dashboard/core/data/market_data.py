# core/data/market_data.py

import yfinance as yf
import pandas as pd
import numpy as np

from core.data.ticker_validation import validate_or_fix_ticker

def load_asset_series(ticker, start="2010-01-01", end=None):
    ticker = validate_or_fix_ticker(ticker)

    if ticker is None:
        raise ValueError(f"Ticker ungültig oder delisted.")

    data = yf.download(ticker, start=start, end=end, progress=False)

    if data.empty:
        raise ValueError(f"Keine Daten für {ticker}")

    prices = data["Close"].dropna()
    returns = prices.pct_change().dropna()
    dates = returns.index

    return {
        "ticker": ticker,
        "dates": dates,
        "prices": prices.loc[dates].values.reshape(-1),
        "returns": returns.values.reshape(-1),
    }


def get_etf(ticker):
    return load_asset_series(ticker)

def get_gold():
    return load_asset_series("GC=F")  # Gold-Future

def get_bond():
    return load_asset_series("IEF")  # US 7-10y Treasury ETF
