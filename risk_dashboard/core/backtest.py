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
                    {"ticker": "AAPL", "weight_in_etf": 0.30},
                    {"ticker": "MSFT", "weight_in_etf": 0.30},
                    {"ticker": "NVDA", "weight_in_etf": 0.20},
                    {"ticker": "AMZN", "weight_in_etf": 0.20},
                ])

            # Normalisieren falls vorhanden
            if normalize_holdings_df:
                try:
                    hdf = normalize_holdings_df(hdf)
                except Exception as e:
                    logger.warning("normalize_holdings_df failed for %s: %s", etf, e)

            # compute absolute weights (sicher aufrufen)
            try:
                hdf_out = compute_abs_weights(hdf, portfolio_value)
            except Exception as e:
                logger.exception("compute_abs_weights failed for %s: %s", etf, e)
                results["results"][etf] = {"status": "skipped", "reason": "compute_weights_failed"}
                continue

            # ... restliche Backtest‑Logik (prepare_prices_for_backtest, run_portfolio_backtest, speichern) ...

            # --- Preise laden (neu) ---
            # 5) Berechne Preise laden (neu) (falls prepare_prices_for_backtest vorhanden)
            prices = pd.DataFrame()
            try:
                prices = prepare_prices_for_backtest(hdf=hdf, project_root=PROJECT_ROOT, load_price_data_func=load_price_data)
                logger.debug("prepare_prices_for_backtest returned prices with columns: %s", list(prices.columns)[:20])
            except Exception as e:
                logger.exception("prepare_prices_for_backtest failed for %s: %s", etf, e)
                prices = pd.DataFrame()

            logger.debug("prices head: %s", prices.head().to_dict())
            logger.debug("prices index dtype: %s", type(prices.index))

            if prices is None or prices.empty:
                logger.warning("Keine Preisdaten für %s – Backtest übersprungen.", etf)
                results["results"][etf] = {"status": "skipped", "reason": "no_prices"}
                continue

            # --- Close Series extrahieren (robust gegenüber OHLC / MultiIndex) ---
            price_close = extract_close_series(prices)
            logger.debug("price_close columns: %s", list(price_close.columns)[:20])


            # --- Marktwert berechnen (einheitlich über helper) ---
            # compute_market_value_from_holdings entscheidet automatisch zwischen weight_in_etf, shares*last_price oder fallback
            hdf, method = compute_market_value_from_holdings(hdf, price_close, portfolio_value)
            logger.debug("market_value method used: %s", method)
            logger.debug("market_value sample: %s", hdf[["ticker","market_value"]].head().to_dict(orient="records"))

            # --- compute absolute weights (einmalig) ---
            hdf_out = pd.DataFrame()
            try:
                hdf_out = compute_abs_weights(hdf, portfolio_value)  # erwartet 'market_value'
                # hdf_out muss Spalte 'abs_weight' liefern (market_value / portfolio_value)
                weights_for_backtest = (hdf_out.set_index("ticker")["abs_weight"] * portfolio_value).to_dict()
                logger.debug("Computed weights_for_backtest for %s: %s", etf, list(weights_for_backtest.items())[:10])
            except Exception as e:
                logger.exception("compute_abs_weights failed for %s: %s", etf, e)
                results["results"][etf] = {"status": "skipped", "reason": "compute_weights_failed"}
                continue

            # --- run backtest (einmalig) ---
            # 7) Run backtest (falls run_portfolio_backtest vorhanden)
            try:
                bt_output = call_run_portfolio_backtest_safe(
                    run_portfolio_backtest,
                    price_close,
                    weights_for_backtest,
                    macro_df
                )
            except Exception as e:
                logger.exception("run_portfolio_backtest failed for %s: %s", etf, e)
                results.setdefault("results", {})[etf] = {"status": "failed", "error": str(e)}
                continue

            # Ergebnis-Dict initialisieren (vor dem Speichern!)
            results.setdefault("results", {}).setdefault(etf, {})["status"] = "ok"
            results["results"][etf]["backtest"] = bt_output

            # Sicherstellen, dass Zielordner existiert
            backtest_dir.mkdir(parents=True, exist_ok=True)

            # portfolio_value -> CSV
            pv = bt_output.get("portfolio_value")
            if isinstance(pv, pd.Series):
                pv = pv.to_frame("value")

            if isinstance(pv, pd.DataFrame) and not pv.empty:
                pv_path = (backtest_dir / f"{etf}_portfolio_value.csv").resolve()
                try:
                    pv.to_csv(pv_path, index=True)
                    logger.info("Wrote portfolio CSV: %s", pv_path)
                    results.setdefault("portfolio_value_files", {})[etf] = str(pv_path)
                    results["results"][etf]["portfolio_value_file"] = str(pv_path)
                except Exception as e:
                    logger.exception("Fehler beim Schreiben der portfolio CSV: %s", e)
                    results["results"][etf]["portfolio_value_file_error"] = str(e)
            else:
                results["results"][etf]["portfolio_value_file"] = None

            # metrics -> JSON
            metrics = bt_output.get("metrics", {})
            metrics_path = backtest_dir / f"{etf}_metrics.json"
            if metrics:
                with open(metrics_path, "w", encoding="utf-8") as f:
                    json.dump(metrics, f, indent=2)
                results.setdefault("metrics_files", {})[etf] = str(metrics_path)
                results["results"][etf]["metrics_file"] = str(metrics_path)

            # weights_over_time -> CSV
            wot = bt_output.get("weights_over_time")
            if isinstance(wot, pd.DataFrame) and not wot.empty:
                wot_path = (backtest_dir / f"{etf}_weights_over_time.csv").resolve()
                wot.to_csv(wot_path, index=True)
                results["results"][etf]["weights_over_time_file"] = str(wot_path)

            st.success(f"Backtest für {etf} abgeschlossen.")
            logger.info("Backtest für %s abgeschlossen.", etf)


        except Exception as exc:
            logger.exception("Uncaught error for %s: %s", etf, exc)
            results["results"][etf] = {"status": "error", "error": str(exc)}
            continue

    return results


def compute_metrics_from_series(portfolio_values: pd.Series, trading_days: int = 252) -> Dict[str, Any]:
    returns = portfolio_values.pct_change().dropna()
    if returns.empty:
        return {"cagr": float("nan"), "vol": float("nan"), "sharpe": float("nan"), "max_dd": float("nan")}
    days = (portfolio_values.index[-1] - portfolio_values.index[0]).days
    total_return = portfolio_values.iloc[-1] / portfolio_values.iloc[0] - 1
    cagr = (1 + total_return) ** (365.0 / days) - 1 if days > 0 else float("nan")
    vol = returns.std() * np.sqrt(trading_days)
    sharpe = (returns.mean() * trading_days) / vol if vol > 0 else float("nan")
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = cum / peak - 1
    max_dd = drawdown.min()
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "max_dd": max_dd}

def run_portfolio_backtest (
    prices_df: pd.DataFrame,
    weights: Dict[str, float],
    start: str = None,
    end: str = None,
    rebalance: str = "monthly"
) -> Dict[str, Any]:
    """
    Simple weighted portfolio backtest with periodic rebalancing.
    prices_df: DataFrame indexed by Date with tickers as columns (Close prices).
    weights: dict ticker -> weight (not necessarily normalized).
    rebalance: 'monthly', 'quarterly', 'yearly', or 'none'
    Returns dict with portfolio_value Series, metrics dict, weights_over_time DataFrame.
    """

    # 1) Schutzschicht: Keine Holdings → kein Backtest
    if not weights or all(v == 0 for v in weights.values()):
        logger.debug("WARN: Keine gültigen Holdings‑Gewichte – Backtest übersprungen.")
        return {
            "portfolio_value": pd.Series(dtype=float),
            "metrics": {},
            "weights_over_time": pd.DataFrame()
        }

    # 2) Preise prüfen
    if prices_df is None or prices_df.empty:
        return {"portfolio_value": pd.Series(dtype=float), "metrics": {}, "weights_over_time": pd.DataFrame()}

    df = prices_df.copy()

    # 3) Zeitraum filtern
    if start:
        df = df[df.index >= pd.to_datetime(start)]
    if end:
        df = df[df.index <= pd.to_datetime(end)]
    df = df.dropna(how="all")
    if df.empty:
        return {"portfolio_value": pd.Series(dtype=float), "metrics": {}, "weights_over_time": pd.DataFrame()}

    # 4) Nur Ticker verwenden, die in Preisen existieren
    tickers = [t for t in weights.keys() if t in df.columns]
    if not tickers:
        logger.warning("No tickers from weights present in prices_df")
        return {"portfolio_value": pd.Series(dtype=float), "metrics": {}, "weights_over_time": pd.DataFrame()}

    # 5) Normalisierte Gewichte
    w = np.array([weights[t] for t in tickers], dtype=float)
    w = w / w.sum()

    price = df[tickers].ffill().dropna(how="all")
    returns = price.pct_change().fillna(0)

    # 6) Rebalancing-Daten
    if rebalance == "monthly":
        reb_dates = price.resample("ME").last().index
    elif rebalance == "quarterly":
        reb_dates = price.resample("QE").last().index
    elif rebalance == "yearly":
        reb_dates = price.resample("A").last().index
    else:
        reb_dates = [price.index[0]]

    # 7) Portfolio simulieren
    pv = pd.Series(index=price.index, dtype=float)
    portfolio_value = 1.0
    holdings = (w * portfolio_value) / price.iloc[0]
    pv.iloc[0] = portfolio_value

    weights_over_time = {price.index[0]: dict(zip(tickers, w))}

    for i in range(1, len(price.index)):
        date = price.index[i]
        portfolio_value = (holdings * price.iloc[i]).sum()
        pv.iloc[i] = portfolio_value

        if date in reb_dates:
            target_values = portfolio_value * w
            holdings = target_values / price.loc[date]
            weights_over_time[date] = dict(zip(tickers, w))

    weights_df = pd.DataFrame(weights_over_time).T if weights_over_time else pd.DataFrame()
    metrics = compute_metrics_from_series(pv)

    return {
        "portfolio_value": pv,
        "metrics": metrics,
        "weights_over_time": weights_df
    }


def call_run_portfolio_backtest_safe(func, price_close, weights_for_backtest, macro_df):
    sig = inspect.signature(func)
    params = sig.parameters

    # Versuche kwargs mit bekannten Namen
    candidate_kwargs = {
        "prices": price_close,
        "price_close": price_close,
        "price_df": price_close,
        "prices_df": price_close,
        "prices_series": price_close,
        "weights": weights_for_backtest,
        "weights_for_backtest": weights_for_backtest,
        "macro_df": macro_df,
        "macro": macro_df,
    }

    # Wähle nur die Keys, die in der Signatur vorkommen
    kwargs = {k: v for k, v in candidate_kwargs.items() if k in params}

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
