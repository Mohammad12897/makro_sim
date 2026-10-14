# risk_dashboard/backtest_utils.py
from typing import Tuple

import pandas as pd
import streamlit as st
from core.macro_pipeline import prepare_for_backtest, run_backtest
from risk_dashboard.ticker_utils import normalize_weights_keys


def compute_common_range(df: pd.DataFrame, min_overlap_days: int = 200) -> Tuple[pd.DatetimeIndex, list]:
    if df is None or df.empty:
        return None, []
    # per-column valid ranges
    ranges = {}
    for c in df.columns:
        s = df[c].dropna()
        if s.empty:
            ranges[c] = (None, None)
        else:
            ranges[c] = (s.index.min(), s.index.max())
    # compute intersection
    starts = [r[0] for r in ranges.values() if r[0] is not None]
    ends = [r[1] for r in ranges.values() if r[1] is not None]
    if not starts or not ends:
        return None, list(df.columns)
    common_start = max(starts)
    common_end = min(ends)
    if common_start is None or common_end is None or common_start >= common_end:
        # no common range
        return None, list(df.columns)
    # check per-ticker overlap length
    removed = []
    for c, (s,e) in ranges.items():
        if s is None or e is None:
            removed.append(c)
            continue
        overlap_days = (min(e, common_end) - max(s, common_start)).days
        if overlap_days < min_overlap_days:
            removed.append(c)
    common_index = pd.date_range(start=common_start, end=common_end, freq='D')
    return common_index, removed


def on_run_backtest():
    # Beispiel: in app.py, wenn Backtest gestartet wird
    combined = st.session_state.get("prices_for_bt", pd.DataFrame())
    weights = normalize_weights_keys(st.session_state.get("weights_by_ticker", {}), list(combined.columns))
    st.session_state["weights_for_bt"] = weights

    prices_bt, weights_bt, removed = prepare_for_backtest(combined, weights, min_overlap_days=180)
    if prices_bt is None or not weights_bt:
        st.error("Insufficient common price data. Entfernte Ticker: " + ", ".join(removed))
        return
    else:
        # call your backtest with prices_bt and weights_bt
        result = run_backtest(prices_bt, weights_bt)
        st.session_state["last_backtest_result"] = result
