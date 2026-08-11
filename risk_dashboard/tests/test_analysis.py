# tests/test_analysis.py (oben einfügen)
import sys
import os

# Repo root (zwei Ebenen über risk_dashboard/tests)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

# Importiere die zu testenden Funktionen
from risk_dashboard.core.analysis import (
    _normalize_input_tickers,
    extract_close_series_for_used,
    analyze_ticker,
)

# Hilfsfunktion: Erzeuge Datumsindex
def make_dates(n=10, tz="UTC"):
    start = pd.Timestamp("2026-07-01", tz=tz)
    return pd.date_range(start, periods=n, freq="D")

def test_normalizer():
    assert _normalize_input_tickers('"AAPL, CSPX.L"') == ["AAPL", "CSPX.L"]
    assert _normalize_input_tickers(" aapl ; msft ") == ["AAPL", "MSFT"]
    assert _normalize_input_tickers("") == []
    assert _normalize_input_tickers("'googl|amzn'") == ["GOOGL", "AMZN"]

def test_extract_close_flat_columns():
    dates = make_dates(5)
    df = pd.DataFrame({
        "AAPL Close": [150.0, 151.0, 152.5, 153.0, 154.0],
        "CSPX.L Close": [100.0, 101.0, 102.0, 103.0, 104.0],
    }, index=dates)
    s = extract_close_series_for_used(df, "AAPL")
    assert isinstance(s, pd.Series)
    assert len(s) == 5
    assert s.iloc[0] == 150.0

def test_extract_close_multiindex_columns():
    dates = make_dates(4)
    cols = pd.MultiIndex.from_tuples([
        ("AAPL", "Open"), ("AAPL", "Close"),
        ("CSPX.L", "Close"), ("CSPX.L", "Volume")
    ])
    df = pd.DataFrame([
        [1, 10, 100, 1000],
        [2, 11, 101, 1100],
        [3, 12, 102, 1200],
        [4, 13, 103, 1300],
    ], index=dates, columns=cols)
    s = extract_close_series_for_used(df, "AAPL")
    assert isinstance(s, pd.Series)
    assert list(s) == [10, 11, 12, 13]

def test_extract_close_stacked_index():
    # gestapeltes DataFrame mit MultiIndex-Index, Level '__ticker'
    dates = make_dates(3)
    # Erzeuge MultiIndex: (ticker, date)
    tuples = []
    values = []
    for ticker in ["AAPL", "CSPX.L"]:
        for d in dates:
            tuples.append((ticker, d))
            values.append(100.0 if ticker == "AAPL" else 200.0)
    index = pd.MultiIndex.from_tuples(tuples, names=["__ticker", "date"])
    df = pd.DataFrame({"Close": values}, index=index)
    # xs auf Level '__ticker' sollte funktionieren
    s = extract_close_series_for_used(df, "AAPL")
    assert isinstance(s, pd.Series)
    assert all(s == 100.0)

def test_analyze_ticker_fallback_to_cached(monkeypatch):
    """
    Simuliere:
      - load_raw_prices_for_universe liefert ein prices_multi, in dem AAPL-Spalte nur NaN
      - load_price_data_cached_with_used liefert ein cached df mit echten AAPL-Werten
    Prüfe, dass analyze_ticker close_series aus cached df verwendet.
    """
    dates = make_dates(6)
    # prices_multi: AAPL column exists but all NaN
    prices_multi = pd.DataFrame({
        "AAPL": [np.nan] * len(dates),
        "CSPX.L": [1,2,3,4,5,6],
    }, index=dates)

    # cached single-df with long history (non-empty numeric column)
    cached_dates = pd.date_range("2020-01-01", periods=10, freq="D")
    cached_df = pd.DataFrame({"AAPL": np.linspace(100, 109, 10)}, index=cached_dates)

    # monkeypatch die Datenladefunktionen, die analyze_ticker intern verwendet
    def fake_load_raw_prices_for_universe(universe):
        # return the small prices_multi and no skipped tickers
        return prices_multi, []

    def fake_load_price_data_cached_with_used(used):
        # return used_loaded flag and the cached df
        return used, cached_df

    monkeypatch.setattr("risk_dashboard.core.analysis.load_raw_prices_for_universe", fake_load_raw_prices_for_universe)
    monkeypatch.setattr("risk_dashboard.core.analysis.load_price_data_cached_with_used", fake_load_price_data_cached_with_used)

    # call analyze_ticker with AAPL in input; etf_universe can be empty
    used, close_series, metrics, pm = analyze_ticker("AAPL", [])
    assert used == "AAPL"
    assert isinstance(close_series, pd.Series)
    # close_series should come from cached_df (non-empty)
    assert len(close_series) > 0
    # metrics should be computed (or at least not raise)
    assert isinstance(metrics, dict) or metrics is None
