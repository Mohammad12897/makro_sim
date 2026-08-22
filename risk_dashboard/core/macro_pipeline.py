# risk_dashboard/core/macro_pipeline.py (Ausschnitt hinzufügen)
from unittest import result
import numpy as np
import pandas as pd
import yfinance as yf
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
def _fetch_and_clean_prices(tickers, start=None, end=None):
    valid = {}
    removed = []

    for t in tickers:
        try:
            df = yf.download(t, start=start, end=end, progress=False)
        except Exception as e:
            logger.debug("yfinance download failed for %s: %s", t, e)
            df = None

        if df is None or df.empty:
            logger.debug("No data for %s (df is None or empty).", t)
            removed.append(t)
            continue

        # Wenn MultiIndex-Spalten vorliegen (z.B. ('Close','NVDA')), handle das
        series = None
        cols = df.columns

        # 1) MultiIndex-Fall: suche ('Adj Close', t) oder ('Close', t)
        if isinstance(cols, pd.MultiIndex):
            # Versuche zuerst ('Adj Close', ticker), dann ('Close', ticker)
            candidates = [('Adj Close', t), ('Close', t)]
            for cand in candidates:
                if cand in cols:
                    series = df[cand].dropna()
                    break
            # Falls nicht gefunden: versuche level 0 'Adj Close' und level 1 ticker
            if series is None:
                try:
                    # xs auf level=0 (z. B. 'Adj Close') und dann Spalte ticker
                    if 'Adj Close' in cols.get_level_values(0):
                        tmp = df.xs('Adj Close', axis=1, level=0)
                        if t in tmp.columns:
                            series = tmp[t].dropna()
                    if series is None and 'Close' in cols.get_level_values(0):
                        tmp = df.xs('Close', axis=1, level=0)
                        if t in tmp.columns:
                            series = tmp[t].dropna()
                except Exception:
                    series = None

        else:
            # 2) Single‑level-Fall: suche 'Adj Close' oder 'Close'
            if 'Adj Close' in cols:
                series = df['Adj Close'].dropna()
            elif 'Close' in cols:
                series = df['Close'].dropna()
            else:
                # Falls keine erwarteten Spalten, versuche die erste numerische Spalte
                numeric_cols = df.select_dtypes(include='number').columns
                if len(numeric_cols) > 0:
                    series = df[numeric_cols[0]].dropna()

        # 3) Validierung der Series
        if series is None or series.empty:
            logger.debug("No valid price series for %s after extraction.", t)
            removed.append(t)
            continue

        # Stelle sicher, dass Index DatetimeIndex ist
        try:
            if not isinstance(series.index, pd.DatetimeIndex):
                series.index = pd.to_datetime(series.index)
        except Exception:
            logger.debug("Could not convert index to DatetimeIndex for %s.", t)

        valid[t] = series

    # Wenn nichts übrig bleibt
    if not valid:
        return pd.DataFrame(), removed

    # concat ist robust gegenüber unterschiedlichen Indizes
    prices_df = pd.concat(valid, axis=1)
    # falls MultiIndex-Spalten entstehen, vereinfachen
    if isinstance(prices_df.columns, pd.MultiIndex):
        prices_df.columns = [c[0] for c in prices_df.columns]
    prices_df = prices_df.sort_index().dropna(how='all')

    return prices_df, removed

def run_backtest(tickers=None, prices_df=None, start=None, end=None,
                 initial_cash=10000, monthly_dca=0, weights=None,
                 strategy="equal", momentum_threshold=0.0, vol_target=None, rebalance="monthly"):
    """
    Entweder prices_df übergeben (vorab geladen) oder tickers übergeben, dann werden Preise geladen.
    Rückgabe: dict mit keys: portfolio_value (Series), metrics (dict), removed_tickers (list)
    """
    removed_tickers = []

    # 1) Preise laden, falls nicht übergeben
    if prices_df is None:
        if not tickers:
            raise ValueError("Keine Ticker übergeben.")
        prices_df, removed_tickers = _fetch_and_clean_prices(tickers, start=start, end=end)
        if prices_df.empty:
            raise ValueError(f"Keine Preisdaten für angefragte Ticker. Entferne: {', '.join(removed_tickers)}")
    else:
        if prices_df.empty:
            raise ValueError("Keine Preisdaten übergeben (prices_df ist leer).")

    # 2) gültige Ticker aus prices_df ableiten
    if tickers is None:
        tickers = prices_df.columns.tolist()
    tickers = [t for t in tickers if t in prices_df.columns]
    if not tickers:
        raise ValueError("Keine gültigen Ticker in prices_df")

    # 3) Vorbereitung
    dates = prices_df.index
    buy_dates = dca_schedule(dates, day_of_month=1) if monthly_dca > 0 else []
    cash = float(initial_cash)
    positions = {t: 0.0 for t in tickers}
    portfolio_values = []

    # 4) --- NEU: Gewichte einmalig setzen und normalisieren (vor initialer Allokation) ---
    if weights is None:
        weights = {t: 1.0/len(tickers) for t in tickers}
    else:
        weights = {t: float(weights.get(t, 0.0)) for t in tickers}
        s = sum(weights.values())
        if s == 0:
            weights = {t: 1.0/len(tickers) for t in tickers}
        else:
            weights = {t: w/s for t, w in weights.items()}
    # ------------------------------------------------------------------------------

    # Initiale Allokation für Buy & Hold: investiere das Startkapital am ersten Handelstag
    if strategy == "buy_and_hold":
        # Kaufe am ersten verfügbaren Datum mit gültigen Preisen
        # Falls das erste Datum NaNs hat, suche das erste Datum mit mindestens einem gültigen Preis
        first_date = None
        for d in dates:
            row = prices_df.loc[d]
            if not row.isna().all():
                first_date = d
                break
        if first_date is None:
            raise ValueError("Keine gültigen Preise für initialen Kauf gefunden.")
        for t, w in weights.items():
            price = prices_df.at[first_date, t] if t in prices_df.columns else None
            if price is not None and not pd.isna(price) and price > 0:
                positions[t] = (cash * w) / price
        cash = 0.0

    # 4) Gewichte: (entferne die komplette Duplikat‑Logik hier)
    #    <-- lösche den alten Block, der weights erneut setzt/normalisiert -->

    # 5) Hauptschleife
    for date in dates:
        if date in buy_dates:
            alloc = allocate_cash_to_weights(monthly_dca, weights)
            for t, value in alloc.items():
                price = prices_df.at[date, t] if t in prices_df.columns else None
                if price is not None and not pd.isna(price) and price > 0:
                    positions[t] += value / price
            cash -= monthly_dca

        pv = 0.0
        for t in tickers:
            price = prices_df.at[date, t]
            if not pd.isna(price):
                pv += positions[t] * price
        total_value = pv + cash
        portfolio_values.append(total_value)

        # Vol target (monatlich)
        next_idx = dates.get_loc(date) + 1
        is_month_end = (next_idx == len(dates)) or (dates[next_idx].month != date.month)
        if vol_target and is_month_end and len(portfolio_values) > 1:
            pv_series_tmp = pd.Series(portfolio_values, index=dates[:len(portfolio_values)])
            port_rets = pv_series_tmp.pct_change().dropna()
            lev = vol_target_leverage(port_rets, target_vol=vol_target, cap=2.0, window=63)
            if lev is not None and lev > 0:
                for t in positions:
                    positions[t] *= lev

    pv_series = pd.Series(portfolio_values, index=dates)

    # 6) Kennzahlen
    metrics = {"final_value": None, "cagr": None, "max_dd": None}
    if not pv_series.empty:
        metrics["final_value"] = float(pv_series.iloc[-1])
        try:
            years = (pv_series.index[-1] - pv_series.index[0]).days / 365.25
            metrics["cagr"] = (pv_series.iloc[-1] / pv_series.iloc[0]) ** (1/years) - 1 if years > 0 else None
            cummax = pv_series.cummax()
            dd = (pv_series - cummax) / cummax
            metrics["max_dd"] = float(dd.min())
        except Exception:
            pass

    return {"portfolio_value": pv_series, "metrics": metrics, "weights_over_time": None, "removed_tickers": removed_tickers}

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