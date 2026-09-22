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
    # Defensive handling: bt may be None, an envelope, or a raw backtest dict
    if bt is None:
        st.warning("Kein Backtest Ergebnis vorhanden.")
        return

    # If an envelope was passed, unpack it
    if isinstance(bt, dict) and "ok" in bt and "result" in bt:
        if not bt.get("ok"):
            st.warning(bt.get("message", "Backtest fehlgeschlagen."))
            return
        bt = bt.get("result") or {}

    # Now bt should be a dict with keys like 'portfolio_value', 'metrics', 'removed_tickers'
    pv = bt.get("portfolio_value") if isinstance(bt, dict) else None
    metrics = bt.get("metrics", {}) if isinstance(bt, dict) else {}
    removed = bt.get("removed_tickers", []) if isinstance(bt, dict) else []

    if removed:
        st.warning("Folgende Ticker wurden entfernt (keine Preisdaten): "  ", ".join(removed))

    if not metrics and (pv is None or (hasattr(pv, "empty") and pv.empty)):
        st.warning("Backtest lieferte keine Ergebnisse.")
        return

    st.subheader("Backtest Ergebnis")
    st.metric("Finaler Wert", f"{metrics.get('final_value', 0):.2f}")
    st.write("CAGR:", f"{metrics.get('cagr'):.2%}" if metrics.get("cagr") else "n/a")
    st.write("Max Drawdown:", f"{metrics.get('max_dd'):.2%}" if metrics.get("max_dd") else "n/a")

    if pv is not None and isinstance(pv, (pd.Series, pd.DataFrame)) and not pv.empty:
        # normalize to DataFrame with date/value
        if isinstance(pv, pd.Series):
            df = pv.reset_index()
            df.columns = ["date", "value"]
        else:
            # DataFrame: try to find a single value column or use first numeric column
            numeric = pv.select_dtypes(include="number")
            if numeric.shape[1] == 0:
                st.warning("portfolio_value enthält keine numerischen Werte.")
            else:
                df = numeric.iloc[:, [0]].reset_index()
                df.columns = ["date", "value"]

        chart = alt.Chart(df).mark_line().encode(
            x="date:T",
            y="value:Q"
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Kein Portfolio‑Wert zum Plotten vorhanden.")




def safe_backtest_call(fn, *args, prices_df=None, available=None, **kwargs):
     # Filter
    removed = []
    if prices_df is not None and available is not None:
        original_available = list(available)
        available = [t for t in available if t in prices_df.columns]
        removed = [t for t in original_available if t not in available]
        if not available:
            # Return envelope with removed tickers information
            return {"ok": False, "message": "Keine der ausgewählten Ticker in den Preisdaten vorhanden.", "result": {"removed_tickers": removed}}
        kwargs["prices_df"] = prices_df[available]
 
     # Debug log
    logger.debug("safe_backtest_call calling %s with args=%s kwargs_keys=%s", fn.__name__, args, list(kwargs.keys()))

    res = maybe_run_backtest(fn, *args, **kwargs) or {}

    # Ensure removed_tickers is present in the returned envelope/result
    if isinstance(res, dict):
        # If envelope already present, ensure result dict exists
        if "result" not in res or res["result"] is None:
            res["result"] = {}
        # merge removed tickers (preserve any existing list)
        existing_removed = res["result"].get("removed_tickers", [])
        # combine and deduplicate while preserving order
        combined = []
        for t in (existing_removed + removed):
            if t not in combined:
                combined.append(t)
        if combined:
            res["result"]["removed_tickers"] = combined
    return res
