# risk_dashboard/utils/backtest_adapter.py
from typing import Any, Dict

import numpy as np
import streamlit as st
import pandas as pd
from data_utils import normalize_prices
from risk_dashboard.core.backtest import run_backtest_flow


import logging

logger = logging.getLogger(__name__)


def _extract_tickers(arg: Any):
    if isinstance(arg, dict):
        if "tickers" in arg and arg["tickers"]:
            return list(arg["tickers"])
        if "weights" in arg and isinstance(arg["weights"], dict):
            return list(arg["weights"].keys())
    if isinstance(arg, (list, tuple)):
        return list(arg)
    return []


def _resolve_tickers(portfolio_or_tickers, args, kwargs):
    """
    Liefert eine Liste normalisierter Ticker zurück.
    Akzeptiert:
      - portfolio_or_tickers: list|tuple|str
      - args: zusätzliche positional args (erste kann Liste/String sein)
      - kwargs: optionales dict mit "tickers"
    """
    tickers = None

    # 1) direkte Übergabe
    if isinstance(portfolio_or_tickers, (list, tuple)):
        tickers = list(portfolio_or_tickers)
    elif isinstance(portfolio_or_tickers, str):
        tickers = [portfolio_or_tickers]

    # 2) kwargs fallback
    if not tickers:
        t_from_kwargs = kwargs.get("tickers")
        if isinstance(t_from_kwargs, (list, tuple)):
            tickers = list(t_from_kwargs)
        elif isinstance(t_from_kwargs, str):
            tickers = [t_from_kwargs]

    # 3) args fallback (z. B. adapter_runbacktest(..., ["A","B"]))
    if not tickers and args:
        first = args[0]
        if isinstance(first, (list, tuple)):
            tickers = list(first)
        elif isinstance(first, str):
            tickers = [first]

    if not tickers:
        return []

    # 4) normalize and uppercase (use your normalize_ticker helper)
    from risk_dashboard.ticker_utils import normalize_ticker
    tickers_norm = []
    for t in tickers:
        if not t:
            continue
        tn = normalize_ticker(str(t)).strip().upper()
        if tn:
            tickers_norm.append(tn)
    # deduplicate preserving order
    seen = set()
    result = []
    for t in tickers_norm:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result

def adapter_run_backtest(portfolio_or_tickers, *args, **kwargs):
    ss = kwargs.get("ss") or __import__("streamlit").session_state
    prefix = kwargs.get("prefix", "profile")

    prices_df = kwargs.get("prices") or kwargs.get("prices_df") or ss.get("prices_for_bt")
    weights_map = kwargs.get("weights") or kwargs.get("user_weights") or ss.get("weights_by_ticker", {})

    if prices_df is None or (isinstance(prices_df, pd.DataFrame) and prices_df.empty):
        return {"ok": False, "error": "no_price_data", "message": "Preisdaten fehlen oder sind leer", "result": {}}
    if not weights_map:
        return {"ok": False, "error": "no_weights", "message": "Keine Gewichte vorhanden", "result": {}}

    # normalize weights against actual price columns
    from risk_dashboard.ticker_utils import normalize_weights_keys
    weights_norm = normalize_weights_keys(weights_map, list(prices_df.columns))

    # determine tickers (unchanged)
    tickers = _resolve_tickers(portfolio_or_tickers, args, kwargs)
    if not tickers:
        return {"ok": False, "message": "Keine Ticker übergeben", "result": {}}

    try:
        bt_response = run_backtest_flow(
            ss=ss,
            prefix=prefix,
            price_data=prices_df,
            weights_map=weights_norm,
            min_common_days=kwargs.get("min_common_days", 250),
            initial_cash=kwargs.get("initial_cash", 100000),
            strategy=kwargs.get("strategy", "equal"),
            rebalance=kwargs.get("rebalance", "monthly"),
        )
        return bt_response
    except Exception as e:
        logger.exception("adapter_run_backtest unexpected error: %s", e)
        return {"ok": False, "error": "internal_error", "message": f"Adapter Fehler: {e}", "result": {}}
