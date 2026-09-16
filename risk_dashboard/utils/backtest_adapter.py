# risk_dashboard/utils/backtest_adapter.py
from typing import Any, Dict

import numpy as np
import streamlit as st
from risk_dashboard.core.macro_pipeline import run_backtest
from risk_dashboard.core.backtest import preflight_check

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

def adapter_run_backtest(portfolio_or_tickers, *args, **kwargs):
    import logging
    logger = logging.getLogger(__name__)

    # 1) normalize tickers: accept positional list or kwargs["tickers"]
    tickers = None
    if isinstance(portfolio_or_tickers, (list, tuple)):
        tickers = list(portfolio_or_tickers)
    elif isinstance(portfolio_or_tickers, str):
        tickers = [portfolio_or_tickers]
    else:
        tickers = kwargs.get("tickers")

    # fallback: try args[0] if still None
    if not tickers and args:
        first = args[0]
        if isinstance(first, (list, tuple)):
            tickers = list(first)
        elif isinstance(first, str):
            tickers = [first]

    if not tickers:
        return {"ok": False, "message": "Keine Ticker übergeben", "result": {}}

    # 2) map prices -> prices_df (avoid truthiness check on DataFrame)
    prices_df = kwargs.get("prices", None)
    if prices_df is None:
        prices_df = kwargs.get("prices_df", None)
    logger.debug("adapter_run_backtest: prices_df present=%s shape=%s",
                    prices_df is not None, getattr(prices_df, "shape", None))

    # 3) unify weights names
    weights = kwargs.get("weights") or kwargs.get("user_weights") or kwargs.get("portfolio_weights")

    # 4) unify start/end and initial cash
    start = kwargs.get("start") or kwargs.get("start_date")
    end = kwargs.get("end") or kwargs.get("end_date")
    initial_cash = kwargs.get("initial_cash", 10000)

    # 5) quick sanity
    if prices_df is None:
        return {"ok": False, "message": "Preisdaten fehlen (prices/prices_df ist None)", "result": {}}
    if getattr(prices_df, "empty", False):
        return {"ok": False, "message": "Preisdaten sind leer", "result": {}}
        missing = [t for t in tickers if t not in prices_df.columns]
        if missing:
            return {"ok": False, "message": f"Fehlende Preisspalten: {missing}", "result": {}}

    # optional: normalize weights if provided as dict and sum != 1
    if isinstance(weights, dict):
        try:
            total_w = sum(float(v) for v in weights.values())
        except Exception:
            logger.debug("adapter_run_backtest: weights not numeric")
            total_w = None
        if total_w:
            if abs(total_w - 1.0) > 1e-6:
                logger.debug("adapter_run_backtest: normalizing weights sum=%s", total_w)
                weights = {k: float(v) / total_w for k, v in weights.items()}

        ###########################################################
        # Annahme: ss = st.session_state, prefix gesetzt, selected_etfs, price_data, weights vorhanden
        ss = st.session_state
        prefix = "profile"
        selected_tickers = ss.get(f"{prefix}_selected_etfs", []) or []
        # optional: auch Ticker aus "selected_from_portfolio" berücksichtigen

        valid, removed, common = preflight_check(selected_tickers, price_data=prices_df, min_common_days=250)

        # UI Feedback
        st.info(f"Valid tickers: {valid}")
        if removed:
            st.warning(f"Folgende Ticker wurden entfernt, weil keine oder unzureichende Daten vorhanden sind: {', '.join(removed)}")

        if common is None or common.shape[0] < 30:
            st.error("Nicht genügend gemeinsame Preisdaten für einen sinnvollen Backtest. Bitte wähle andere Ticker oder erweitere das Zeitfenster.")
            # optional: zeige Details
            if common is not None:
                st.write("Gemeinsame Datenpunkte für Backtest:", common.shape)
                st.write("Gemeinsamer Zeitraum:", common.index.min(), "bis", common.index.max())
            # Abbruch: kein Backtest starten
            return

        # Optional: zeige gemeinsame Datenstatistiken
        st.write("Gemeinsame Datenpunkte für Backtest:", common.shape)
        st.write("Gemeinsamer Zeitraum:", common.index.min(), "bis", common.index.max())

        # Gewichte prüfen / normalisieren
        w = np.array([weights.get(t, 0.0) for t in valid], dtype=float)
        if w.sum() == 0:
            st.error("Summe der Gewichte ist 0. Bitte Gewichte anpassen.")
            return
        w = w / w.sum()

        ###########################################################

        # 6) call run_backtest (adapt params as needed)
        try:
            res = run_backtest(
                tickers=tickers,
                prices_df=prices_df,
                start=start,
                end=end,
                initial_cash=initial_cash,
                monthly_dca=kwargs.get("monthly_dca", 0),
                weights=weights,
                strategy=kwargs.get("strategy", "equal"),
                rebalance=kwargs.get("rebalance", "monthly"),
            )
        except Exception as e:
            logger.exception("run_backtest failed")
            return {"ok": False, "message": f"run_backtest error: {e}", "result": {}}

        # 7) normalize return envelope expected by UI
        if isinstance(res, dict):
            return {"ok": True, "message": "ok", "result": res}
        else:
            return {"ok": True, "message": "ok", "result": {"portfolio_value": res}}