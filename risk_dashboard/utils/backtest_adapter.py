# risk_dashboard/utils/backtest_adapter.py
from typing import Any, Dict

import numpy as np
import streamlit as st
import pandas as pd
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

def adapter_run_backtest(portfolio_or_tickers, *args, **kwargs):
    ss = kwargs.get("ss") or __import__("streamlit").session_state
    prefix = kwargs.get("prefix", "profile")

    # safe checks (no truthiness on DataFrame)
    prices_df = kwargs.get("prices") or kwargs.get("prices_df") or ss.get("prices_for_bt")
    weights_map = kwargs.get("weights") or kwargs.get("user_weights") or ss.get("weights_by_ticker", {})

    if prices_df is None or (isinstance(prices_df, pd.DataFrame) and prices_df.empty):
        return {"ok": False, "error": "no_price_data", "message": "Preisdaten fehlen oder sind leer", "result": {}}
    if not weights_map:
        return {"ok": False, "error": "no_weights", "message": "Keine Gewichte vorhanden", "result": {}}


    # normalize tickers (wie du hattest)
    tickers = None
    if isinstance(portfolio_or_tickers, (list, tuple)):
        tickers = list(portfolio_or_tickers)
    elif isinstance(portfolio_or_tickers, str):
        tickers = [portfolio_or_tickers]
    else:
        tickers = kwargs.get("tickers")
    if not tickers and args:
        first = args[0]
        if isinstance(first, (list, tuple)):
            tickers = list(first)
        elif isinstance(first, str):
            tickers = [first]
    if not tickers:
        return {"ok": False, "message": "Keine Ticker übergeben", "result": {}}


    # call central flow and return envelope
    try:
        bt_response = run_backtest_flow(
            ss=ss,
            prefix=prefix,
            price_data=prices_df,
            weights_map=weights_map,
            min_common_days=kwargs.get("min_common_days", 250),
            initial_cash=kwargs.get("initial_cash", 100000),
            strategy=kwargs.get("strategy", "equal"),
            rebalance=kwargs.get("rebalance", "monthly"),
        )
        return bt_response
    except Exception as e:
        logger.exception("adapter_run_backtest unexpected error: %s", e)
        return {"ok": False, "error": "internal_error", "message": f"Adapter Fehler: {e}", "result": {}}

def adapter_run_backtest_old(portfolio_or_tickers, *args, **kwargs):
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

        # 6) call run_backtest (adapt params as needed)
        ############################################################
        from risk_dashboard.core.backtest import run_backtest_flow

        # sicherstellen: ss und prefix sind gesetzt
        ss = st.session_state
        prefix = "profile"
        # Default envelope
        # in adapter_run_backtest
        bt_response = {"ok": False, "error": "internal_error", "message": "Backtest nicht ausgeführt", "result": {}}
        try:
            prices_df = kwargs.get("prices")
            if prices_df is None:
                prices_df = ss.get("prices_for_bt")

            weights_map = kwargs.get("weights")
            if weights_map is None:
                weights_map = ss.get("weights_by_ticker", {})

            # korrekte emptiness checks
            import pandas as pd
            if prices_df is None or (isinstance(prices_df, pd.DataFrame) and prices_df.empty):
                return {"ok": False, "error": "no_data", "message": "Keine Preisdaten vorhanden", "result": {}}
            if not weights_map:
                return {"ok": False, "error": "no_weights", "message": "Keine Gewichte vorhanden", "result": {}}

            bt_response = run_backtest_flow(
                ss=ss,
                prefix=prefix,
                price_data=prices_df,
                weights_map=weights_map,
                min_common_days=kwargs.get("min_common_days", 250),
                initial_cash=kwargs.get("initial_cash", 100000),
                strategy=kwargs.get("strategy", "equal"),
                rebalance=kwargs.get("rebalance", "monthly"),
            )



            resp = bt_response or {}
            # temporär
            st.write("BACKTEST RESULT ENVELOPE:", resp)

            payload = resp.get("payload", {}) or {}
            res = resp.get("result", {}) or {}

            if not resp.get("ok"):
                st.warning(resp.get("message", "Backtest fehlgeschlagen."))
                if payload.get("removed"):
                    st.warning("Entfernte Ticker: " + ", ".join(payload["removed"]))
            else:
                pv = res.get("portfolio_value")
                metrics = res.get("metrics", {})
                if pv is None:
                    st.warning("Kein Backtest‑Ergebnis (portfolio_value fehlt).")
                else:
                    st.line_chart(pv)
                    st.write(metrics)
                    trades_df = pd.DataFrame(res.get("trades", []))
                    st.dataframe(trades_df)
                    if not trades_df.empty:
                        csv = trades_df.to_csv(index=False)
                        st.download_button("Export trades CSV", data=csv, file_name="trades.csv")

            # Defensive UI‑Verarbeitung des Envelope
            if not bt_response or not bt_response.get("ok"):
                st.error(bt_response.get("message", "Backtest fehlgeschlagen"))
                payload = bt_response.get("payload") or {}
                if payload.get("removed"):
                    st.warning("Entfernte Ticker: " + ", ".join(payload["removed"]))
                if payload.get("common_shape"):
                    st.info(f"Gemeinsame Handelstage: {payload['common_shape']}")
            else:
                res = bt_response.get("result", {})
                if isinstance(res, dict) and "portfolio_value" in res:
                    st.line_chart(res["portfolio_value"])
                    st.write(res.get("metrics", {}))
                    trades_df = pd.DataFrame(res.get("trades", []))
                    st.dataframe(trades_df)
                    if not trades_df.empty:
                        csv = trades_df.to_csv(index=False)
                        st.download_button("Export trades CSV", data=csv, file_name="trades.csv")
                else:
                    st.error("Backtest lieferte kein Ergebnis.")
            return bt_response

        except Exception as e:
            logger.exception("adapter_run_backtest unexpected error: %s", e)
            return {"ok": False, "error": "internal_error", "message": f"Adapter Fehler: {e}", "result": {}}

        ###########################################################