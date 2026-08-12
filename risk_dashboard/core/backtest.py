# risk_dashboard/core/backtest.py
import traceback
import inspect
import numpy as np
import pandas as pd
from typing import Dict, Any
import logging
import json, sys,os
from pathlib import Path
from pyparsing import results
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]


logger = logging.getLogger(__name__)

from risk_dashboard.core.data import etf
from risk_dashboard.core.utils import prepare_prices_for_backtest, extract_close_series, compute_market_value_from_holdings

try:
    from risk_dashboard.core.weights import compute_abs_weights
except Exception:
    compute_abs_weights = None
    logger.warning("compute_abs_weights konnte nicht importiert werden; Fallback auf None.")

def run_all_etf_backtests(
    selected_etfs: list,
    holdings_dir: Path,
    etf_to_isin_map: dict,
    price_data: pd.DataFrame,
    macro_df: pd.DataFrame,
    backtest_dir: Path,
    portfolio_value: float = 100000.0,
    output_dir: Path | None = None,
):
    from risk_dashboard.ui.profiles_ui import load_price_data, classify_etf

    if output_dir is not None:
        backtest_dir = Path(output_dir)
    backtest_dir.mkdir(parents=True, exist_ok=True)
    assert os.access(backtest_dir, os.W_OK)
    holdings_dir.mkdir(parents=True, exist_ok=True)
    assert os.access(holdings_dir, os.W_OK)

    results = {"portfolio_value_files": {}, "metrics_files": {}, "results": {}}

    load_holdings_with_fallback = globals().get("load_holdings_with_fallback")
    normalize_holdings_df = globals().get("normalize_holdings_df")

    if price_data is None or price_data.empty:
        st.error("Preisdaten fehlen oder sind leer. Backtest abgebrochen.")
        logger.error("price_data fehlt oder leer")
        return results

    for etf in selected_etfs:
        try:
            # Guard: compute_abs_weights muss callable sein
            if not callable(compute_abs_weights):
                logger.error("compute_abs_weights ist nicht verfügbar; überspringe %s", etf)
                results["results"][etf] = {"status": "skipped", "reason": "compute_weights_missing"}
                continue

            category, tooltip = classify_etf(etf)
            df_key = f"holdings_{etf}"

            # 1) Holdings aus session_state oder Fallback laden
            hdf = st.session_state.get(df_key, pd.DataFrame())
            if hdf is None or (isinstance(hdf, pd.DataFrame) and hdf.empty):
                isin = etf_to_isin_map.get(etf) if etf_to_isin_map else None
                if load_holdings_with_fallback:
                    try:
                        hdf = load_holdings_with_fallback(etf, category, isin, df_key, holdings_dir)
                    except Exception as e:
                        logger.warning("load_holdings_with_fallback failed for %s: %s", etf, e)
                        hdf = pd.DataFrame()
                else:
                    hdf = pd.DataFrame()

            # Demo‑Holdings falls leer
            if hdf is None or (isinstance(hdf, pd.DataFrame) and hdf.empty):
                logger.info("Keine Holdings für %s gefunden — Demo‑Holdings verwenden.", etf)
                hdf = pd.DataFrame([

    # Wenn keine passenden kwargs, versuche positional (häufig: prices, weights, macro_df)
    if not kwargs:
        try:
            return func(price_close, weights_for_backtest, macro_df)
        except TypeError:
            # letzter Versuch: nur prices und weights
            try:
                return func(price_close, weights_for_backtest)
            except TypeError as e:
                raise

    return func(**kwargs)