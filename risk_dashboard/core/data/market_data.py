# core/data/market_data.py (Auszug)
import pandas as pd
import numpy as np
import logging

from core.data.ticker_validation import validate_or_fix_ticker
from risk_dashboard.data_utils import fetch_prices_from_yf, flatten_yf_dataframe

logger = logging.getLogger(__name__)

def load_asset_series(ticker, start="2010-01-01", end=None):
    ticker = validate_or_fix_ticker(ticker)
    if ticker is None:
        raise ValueError("Ticker ungültig oder delisted.")

    df = fetch_prices_from_yf(ticker, start=start, end=end, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"Keine Daten für {ticker}")

    # defensiv flattenen
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = flatten_yf_dataframe(df)
        except Exception:
            pass

    # Bevorzuge Close/Adj Close
    cols_upper = [c.upper() for c in df.columns]
    if any("ADJ" in c and "CLOSE" in c for c in cols_upper):
        col = next(c for c in df.columns if "ADJ" in str(c).upper() and "CLOSE" in str(c).upper())
    elif "CLOSE" in cols_upper:
        col = next(c for c in df.columns if str(c).upper() == "CLOSE")
    else:
        numeric = df.select_dtypes(include="number")
        if numeric.empty:
            raise ValueError(f"Keine numerischen Spalten für {ticker}")
        col = numeric.columns[0]

    prices = df[col].dropna()
    if prices.empty:
        raise ValueError(f"Keine Preise für {ticker}")

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

