# risk_dashboard/data_cache.py
import pandas as pd
import streamlit as st
from typing import Sequence, Tuple, Optional
from risk_dashboard.data_utils import fetch_prices_quiet


@st.cache_data(ttl=24*3600, show_spinner=False)
def load_price_data_cached_with_used(tickers, start="2010-01-01"):
    if isinstance(tickers, str):
        tickers = [tickers]

    used, df = fetch_prices_quiet_with_used(tickers, start=start)
    # ACHTUNG: fetch_prices_quiet_with_used MUSS existieren!

    if df is None:
        df = pd.DataFrame()

    # MultiIndex flatten
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if "Close" in df.columns.get_level_values(0):
                df = df.xs("Close", axis=1, level=0, drop_level=False)
            else:
                df.columns = df.columns.get_level_values(-1)
        except Exception:
            df.columns = df.columns.get_level_values(-1)

    return used, df

@st.cache_data(ttl=24*3600, show_spinner=False)
def load_price_data_cached(tickers, start="2010-01-01"):
    if isinstance(tickers, str):
        tickers = [tickers]

    df = fetch_prices_quiet(tickers, start=start)   # <‑‑ NUR EIN RETURN

    if df is None:
        return pd.DataFrame()

    # MultiIndex flatten
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if "Close" in df.columns.get_level_values(0):
                df = df.xs("Close", axis=1, level=0, drop_level=False)
            else:
                df.columns = df.columns.get_level_values(-1)
        except Exception:
            df.columns = df.columns.get_level_values(-1)

    return df
