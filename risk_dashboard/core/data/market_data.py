
# core/data/market_data.py

import yfinance as yf
import pandas as pd
import numpy as np


def load_asset_series(ticker, start="2010-01-01", end=None):
    data = yf.download(ticker, start=start, end=end, progress=False)

    if data.empty:
        raise ValueError(f"Keine Daten für {ticker}")

    # sichere Preisquelle
    prices = data["Close"].dropna()

    # returns haben automatisch einen eigenen Index
    returns = prices.pct_change().dropna()

    # WICHTIG: returns und dates exakt gleich lang
    dates = returns.index

    return {
        "ticker": ticker,
        "dates": dates,
        "prices": prices.loc[dates].values.reshape(-1),
        "returns": returns.values.reshape(-1),   # <--- 100% 1D
    }


def get_etf(ticker):
    return load_asset_series(ticker)

def get_gold():
    return load_asset_series("GC=F")  # Gold-Future

def get_bond():
    return load_asset_series("IEF")  # US 7-10y Treasury ETF
