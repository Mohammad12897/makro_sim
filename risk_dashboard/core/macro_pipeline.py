# risk_dashboard/core/macro_pipeline.py (Ausschnitt hinzufügen)
from unittest import result
import numpy as np
import pandas as pd
import tempfile, os, json
import streamlit as st
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


from typing import Dict, Any

os.makedirs("risk_dashboard/data", exist_ok=True)

# ---------------------------------------------------------
# 1. Regime erkennen
# ---------------------------------------------------------
def detect_regime(macro_df: pd.DataFrame) -> str:
    """
    Makrodaten → Risiko-Regime.
    Beispiel: Inflation, Zinsstruktur, Wachstum, Arbeitsmarkt.
    """
    score = 0

    if macro_df["inflation"].iloc[-1] > 3:
        score += 1
    if macro_df["yield_curve"].iloc[-1] < 0:
        score += 1
    if macro_df["growth"].iloc[-1] < 0:
        score += 1

    if score >= 2:
        return "risk_off"
    elif score == 1:
        return "neutral"
    else:
        return "risk_on"


# ---------------------------------------------------------
# 2. ETF-Universum pro Regime auswählen
# ---------------------------------------------------------
def select_etfs_for_regime(universe: Dict[str, Dict[str, Any]], regime: str):
    if regime == "risk_off":
        return {k: v for k, v in universe.items() if v["asset_class"] in ["bond", "cash"]}

    if regime == "neutral":
        return {k: v for k, v in universe.items() if v["asset_class"] in ["equity", "bond"]}

    if regime == "risk_on":
        return {k: v for k, v in universe.items() if v["asset_class"] == "equity"}

    return universe


# ---------------------------------------------------------
# 3. Optimierungsmethode wählen
# ---------------------------------------------------------
def optimize_portfolio(prices: pd.DataFrame, method="HRP"):
    """
    Liefert Portfolio-Gewichte basierend auf der gewählten Methode.
    Unterstützt: equal, risk_parity, minvar, HRP.
    """

    # Falls keine Daten → Equal Weight
    if prices is None or prices.empty:
        return {}

    # Returns berechnen
    rets = prices.pct_change().dropna()
    cov = rets.cov()

    # ---------------------------------------------------------
    # 1) Equal Weight
    # ---------------------------------------------------------
    if method == "equal":
        w = {col: 1 / len(prices.columns) for col in prices.columns}
        return w

    # ---------------------------------------------------------
    # 2) Risk Parity (inverse volatility)
    # ---------------------------------------------------------
    if method == "risk_parity":
        vol = np.sqrt(np.diag(cov))
        inv_vol = 1 / vol
        w = inv_vol / inv_vol.sum()
        return dict(zip(prices.columns, w))

    # ---------------------------------------------------------
    # 3) Minimum Variance
    # ---------------------------------------------------------
    if method == "minvar":
        try:
            inv_cov = np.linalg.inv(cov.values)
            ones = np.ones(len(cov))
            w = inv_cov @ ones
            w = w / w.sum()
            return dict(zip(prices.columns, w))
        except Exception:
            # Fallback
            w = {col: 1 / len(prices.columns) for col in prices.columns}
            return w

    # ---------------------------------------------------------
    # 4) HRP (Hierarchical Risk Parity)
    # ---------------------------------------------------------
    if method == "HRP":
        try:
            from scipy.cluster.hierarchy import linkage, leaves_list

            corr = rets.corr()
            dist = np.sqrt(0.5 * (1 - corr.clip(-1, 1)))

            link = linkage(dist, "ward")
            sort_ix = leaves_list(link)
            cov_sorted = cov.iloc[sort_ix, sort_ix]

            # Recursive bisection
            weights = pd.Series(1.0, index=cov_sorted.index)

            def split_cluster(cov_mat, w):
                if len(cov_mat) <= 1:
                    return w
                split = len(cov_mat) // 2
                left = cov_mat.iloc[:split, :split]
                right = cov_mat.iloc[split:, split:]

                var_left = np.sum(left.values)
                var_right = np.sum(right.values)

                alpha = 1 - var_left / (var_left + var_right)

                w[left.index] *= alpha
                w[right.index] *= (1 - alpha)

                w = split_cluster(left, w)
                w = split_cluster(right, w)
                return w

            weights = split_cluster(cov_sorted, weights)
            weights = weights / weights.sum()

            return weights.to_dict()

        except Exception:
            # Fallback
            w = {col: 1 / len(prices.columns) for col in prices.columns}
            return w

    # ---------------------------------------------------------
    # Fallback für unbekannte Methoden
    # ---------------------------------------------------------
    w = {col: 1 / len(prices.columns) for col in prices.columns}
    return w


# ---------------------------------------------------------
# 4. Portfolio pro Regime bauen
# ---------------------------------------------------------
def build_regime_portfolio(regime: str, allowed: Dict[str, Any], method="HRP"):
    tickers = [v["ticker"] for v in allowed.values()]
    # Preise laden → später implementieren
    prices = pd.DataFrame()
    weights = optimize_portfolio(prices, method)
    return weights


# ---------------------------------------------------------
# 5. Backtest
# ---------------------------------------------------------
def run_backtest(weights, prices, regimes=None, start=None, end=None, rebalance="monthly"):
    from risk_dashboard.core.backtest import run_portfolio_backtest
    # Debug
    logger.debug("DEBUG wrapper: calling run_portfolio_backtest; prices type:", type(prices), "weights:", weights)
    # Debug-Ausgaben
    logger.debug("DEBUG wrapper: prices type", type(prices), "shape", getattr(prices, "shape", None))
    logger.debug("DEBUG wrapper: weights", weights, "regimes present:", regimes is not None)

    # optional: slice prices nach start/end
    if start:
        prices = prices[prices.index >= pd.to_datetime(start)]
    if end:
        prices = prices[prices.index <= pd.to_datetime(end)]

    # call the real backtest
    result = run_portfolio_backtest(prices_df=prices, weights=weights, start=start, end=end, rebalance=rebalance)

    pv = result.get("portfolio_value")
    metrics = result.get("metrics", {})
    weights_df = result.get("weights_over_time")

    # write outputs only if present
    if pv is not None and not pv.empty:
        pv_df = pv.rename("portfolio_value").reset_index()
        # speichere DataFrame als dict oder als CSV‑String in session_state
        st.session_state["last_backtest_results_df"] = pv_df  # DataFrame direkt
        st.session_state["last_backtest_results_csv"] = pv_df.to_csv(index=False)
        logger.debug(f"DEBUG: backtest results stored in session_state, {len(pv_df)} Zeilen")
    else:
        logger.debug("DEBUG: portfolio_value leer — keine CSV geschrieben")

    if metrics:
        st.session_state["last_metrics"] = metrics
        logger.debug("DEBUG: results stored in session_state['last_metrics']")
    else:
        logger.debug("DEBUG: metrics leer — keine JSON geschrieben")

    return result


# ---------------------------------------------------------
# 6. Leistungsanalyse
# ---------------------------------------------------------
def analyze_performance(bt_df: pd.DataFrame):
    return {
        "sharpe": 0,
        "volatility": 0,
        "max_drawdown": 0,
    }


# ---------------------------------------------------------
# 7. Optimieren
# ---------------------------------------------------------
def grid_search(params):
    return {}
