# risk_dashboard/core/macro_pipeline.py (Ausschnitt hinzufügen)
from unittest import result
import numpy as np
import pandas as pd
import tempfile, os, json
import streamlit as st
from pathlib import Path
from datetime import datetime
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
def select_etfs_for_regime(universe, macro_regime):
    """
    Unterstützt universe als dict (ticker -> meta) oder als DataFrame.
    Gibt ein dict zurück mit den erlaubten Einträgen für das gegebene Regime.
    """
    # Normalisiere universe in (key, meta) Paare
    if isinstance(universe, dict):
        items = universe.items()
    else:
        # DataFrame: index sollte 'ticker' oder numeric sein; to_dict orient=index liefert meta dicts
        try:
            items = universe.to_dict(orient="index").items()
        except Exception:
            # Fallback: iterate rows
            items = ((row.get("ticker", idx), row.to_dict()) for idx, row in universe.iterrows())

    def keep(v):
        ac = v.get("asset_class") if isinstance(v, dict) else None
        return ac in ["equity", "bond", "cash"]

    # Auswahl je nach macro_regime
    if macro_regime == "risk_off":
        wanted = {"bond", "cash"}
    elif macro_regime == "neutral":
        wanted = {"equity", "bond"}
    elif macro_regime == "risk_on":
        wanted = {"equity"}
    else:
        wanted = None  # kein Filter

    if wanted is None:
        return {k: v for k, v in items}

    return {k: v for k, v in items if (isinstance(v, dict) and v.get("asset_class") in wanted)}


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
def build_regime_portfolio_old(regime: str, allowed: Dict[str, Any], method="HRP"):
    tickers = [v["ticker"] for v in allowed.values()]
    # Preise laden → später implementieren
    prices = pd.DataFrame()
    weights = optimize_portfolio(prices, method)
    return weights

# macro_pipeline.py
def build_regime_portfolio(regime: str, allowed: Dict[str, Any], prices: pd.DataFrame, method="HRP"):
    if prices is None or prices.empty:
        raise ValueError("build_regime_portfolio: 'prices' must be provided and non-empty")
    tickers = [v["ticker"] for v in allowed.values()]
    # benutze die übergebenen prices
    weights = optimize_portfolio(prices.loc[:, tickers], method)
    return {"tickers": tickers, "weights": weights}

def allocate_cash_to_weights(cash_amount, weights):
    if not weights:
        return {}
    s = sum(weights.values())
    if s == 0:
        return {t: 0.0 for t in weights}
    norm = {t: w / s for t, w in weights.items()}
    return {t: cash_amount * norm[t] for t in weights}

def dca_schedule(dates, day_of_month=1):
    return [d for d in dates if d.day == day_of_month]

def vol_target_leverage(port_rets, target_vol=0.10, cap=2.0, window=63):
    if port_rets is None or len(port_rets) < window:
        return 1.0
    rolling_vol = port_rets.rolling(window=window).std() * np.sqrt(252)
    if rolling_vol.empty:
        return 1.0
    current_vol = rolling_vol.iloc[-1]
    if pd.isna(current_vol) or current_vol == 0:
        return 1.0
    lev = float(target_vol / current_vol)
    return max(0.0, min(lev, cap))

# ---------------------------------------------------------
# 5. Backtest
# ---------------------------------------------------------
def run_backtest(tickers, prices_df, start=None, end=None,
                 initial_cash=10000, monthly_dca=0, weights=None,
                 strategy="equal", momentum_threshold=0.0, vol_target=None, rebalance="monthly"):
    
    if prices_df is None or (hasattr(prices_df, "empty") and prices_df.empty):
        raise ValueError("Keine Preisdaten übergeben (prices_df ist leer).")
    # prüfe Spalten/Ticker
    if not tickers:
        raise ValueError("Keine Ticker übergeben.")
    valid = [t for t in tickers if t in prices_df.columns]
    if not valid:
        raise ValueError("Keine gültigen Ticker in prices_df")

    dates = prices_df.index
    # ensure tickers order matches prices_df columns
    tickers = [t for t in tickers if t in prices_df.columns]
    if not tickers:
        raise ValueError("Keine gültigen Ticker in prices_df")

    # prepare
    buy_dates = dca_schedule(dates, day_of_month=1) if monthly_dca > 0 else []
    cash = initial_cash
    positions = {t: 0.0 for t in tickers}  # shares
    portfolio_values = []

    # if no weights provided, equal weight on tickers
    if weights is None or sum(weights.values()) == 0:
        weights = {t: 1.0/len(tickers) for t in tickers}

    # main loop
    for date in dates:
        # DCA execution
        if date in buy_dates:
            alloc = allocate_cash_to_weights(monthly_dca, weights)
            for t, value in alloc.items():
                price = prices_df.at[date, t]
                if not pd.isna(price) and price > 0:
                    positions[t] += value / price
            cash -= monthly_dca

        # compute portfolio value at this date
        pv = 0.0
        for t in tickers:
            price = prices_df.at[date, t]
            if not pd.isna(price):
                pv += positions[t] * price
        total_value = pv + cash
        portfolio_values.append(total_value)

        # apply vol target monthly (example): compute leverage at month end and scale positions
        # check if this date is last trading day of month
        next_idx = dates.get_loc(date) + 1
        is_month_end = (next_idx == len(dates)) or (dates[next_idx].month != date.month)
        if vol_target and is_month_end:
            # compute returns series from portfolio_values so far
            pv_series = pd.Series(portfolio_values, index=dates[:len(portfolio_values)])
            port_rets = pv_series.pct_change().dropna()
            lev = vol_target_leverage(port_rets, target_vol=vol_target, cap=2.0, window=63)
            # scale positions by lev (note: this is a simplification; in real sim you d adjust cash/borrow)
            for t in positions:
                positions[t] *= lev

    pv_series = pd.Series(portfolio_values, index=dates)
    # compute simple metrics
    metrics = {
        "final_value": float(pv_series.iloc[-1]),
        "cagr": None,
        "max_dd": None
    }
    # compute cagr and max drawdown if possible
    try:
        rets = pv_series.pct_change().dropna()
        years = (pv_series.index[-1] - pv_series.index[0]).days / 365.25
        metrics["cagr"] = (pv_series.iloc[-1] / pv_series.iloc[0]) ** (1/years) - 1 if years>0 else None
        cummax = pv_series.cummax()
        dd = (pv_series - cummax) / cummax
        metrics["max_dd"] = float(dd.min())
    except Exception:
        pass

    return {"portfolio_value": pv_series, "metrics": metrics, "weights_over_time": None}


def run_backtest_old(weights, prices, regimes=None, start=None, end=None, rebalance="monthly"):
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