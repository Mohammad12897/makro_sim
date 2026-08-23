# scripts/test_checks.py
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
import re
import inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


import yfinance as yf
from risk_dashboard.core.macro_pipeline import _fetch_and_clean_prices
from risk_dashboard.core.portfolio_sim.covariance import build_asset_covariance
from risk_dashboard.core.data_loader import fetch_prices_safe

from risk_dashboard.core.macro_pipeline import run_backtest   # Beispielname


from risk_dashboard.core.engine.assets import fetch_prices
from risk_dashboard.core.data.market_data import load_asset_series
from risk_dashboard.core.data.caching import cached_fetch_prices


def make_prices():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    df = pd.DataFrame({
        "A": [100, 101, 102, 103],
        "B": [50, 51, 52, 53]
    }, index=dates)
    return df

def test_buy_and_hold_smoke():
    prices = make_prices()
    res = run_backtest(prices_df=prices, strategy="buy_and_hold", initial_cash=1000, monthly_dca=0)
    assert isinstance(res, dict)
    assert "portfolio_value" in res
    assert "metrics" in res
    assert "trades" in res
    assert len(res["trades"]) > 0
