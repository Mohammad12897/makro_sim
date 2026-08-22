# ui/helpers.py
import re
import streamlit as st
import altair as alt
import pandas as pd
import logging

logger = logging.getLogger(__name__)
from risk_dashboard.utils.session_helpers import maybe_run_backtest


def normalize_ticker(t: str) -> str:
    return t.strip().upper()

def detect_type(ticker: str, etf_df=None, stock_df=None) -> str:
    # Prefer explicit lookup in universes if provided
    if etf_df is not None and ticker in etf_df["ticker"].values:
        return "etf"
    if stock_df is not None and ticker in stock_df["ticker"].values:
        return "stock"
    # fallback heuristic
    if re.search(r"\.L|\.DE|\.MI|\.HK|\.TO", ticker, re.IGNORECASE):
        return "etf_or_stock"
    return "stock"

def passes_liquidity(meta_row: dict, min_volume: int = 10000) -> bool:
    vol = meta_row.get("avg_daily_volume") or 0
    try:
        return int(vol) >= int(min_volume)
    except Exception:
        return False

def render_backtest(bt):
    pv = bt["portfolio_value"]
    metrics = bt["metrics"]
    removed = bt.get("removed_tickers", [])

    if removed:
        st.warning("Folgende Ticker wurden entfernt (keine Preisdaten): " + ", ".join(removed))

    st.subheader("Backtest Ergebnis")

    st.metric("Finaler Wert", f"{metrics.get('final_value', 0):.2f}")
    st.write("CAGR:", f"{metrics.get('cagr'):.2%}" if metrics.get("cagr") else "n/a")
    st.write("Max Drawdown:", f"{metrics.get('max_dd'):.2%}" if metrics.get("max_dd") else "n/a")

    if pv is not None and not pv.empty:
        df = pv.reset_index()
        df.columns = ["date", "value"]
        chart = alt.Chart(df).mark_line().encode(
            x="date:T",
            y="value:Q"
        )
        st.altair_chart(chart, use_container_width=True)

def safe_backtest_call(fn, *args, prices_df=None, available=None, **kwargs):
    # Filter
    if prices_df is not None and available is not None:
        available = [t for t in available if t in prices_df.columns]
        if not available:
            return {"ok": False, "message": "Keine der ausgewählten Ticker in den Preisdaten vorhanden.", "result": {}}
        kwargs["prices_df"] = prices_df[available]

    # Debug log
    logger.debug("safe_backtest_call calling %s with args=%s kwargs_keys=%s", fn.__name__, args, list(kwargs.keys()))

    res = maybe_run_backtest(fn, *args, **kwargs) or {}
    return res

