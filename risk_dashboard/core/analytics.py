# risk_dashboard/core/analytics.py
import numpy as np
from typing import Tuple, Optional, List
import pandas as pd
import streamlit as st
import logging


logger = logging.getLogger(__name__)


@st.cache_data
def compute_metrics(close_series: pd.Series, trading_days: int = 252, rf: float = 0.0) -> dict:
    # Defensive: numerisch konvertieren und NA entfernen
    close_series = pd.to_numeric(close_series, errors="coerce").dropna()
    if close_series.empty:
        raise ValueError("Close-Serie ist leer oder enthält keine numerischen Werte")

    rets = close_series.pct_change().dropna()
    ann_ret = (1 + rets.mean()) ** trading_days - 1
    ann_vol = rets.std() * (trading_days ** 0.5)
    sharpe = (ann_ret - rf) / ann_vol if ann_vol != 0 else float("nan")
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    return {
        "annual_return": float(ann_ret),
        "annual_vol": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd)
    }

def analyze_ticker(base_ticker: str, etf_universe: List[str]) -> Tuple[Optional[str], Optional[pd.Series], Optional[dict], Optional[pd.DataFrame]]:
    """
    Lädt Daten für base_ticker (Suffix-Fallbacks), erweitert das Universe,
    lädt Preise für das erweiterte Universe und liefert:
      (used_ticker, close_series, metrics, prices_multi)
    """
    # Lokaler Import, um zirkuläre Importe zu vermeiden
    from risk_dashboard.core.data_loader import fetch_prices_with_suffixes, load_raw_prices_for_universe

    base_ticker = (base_ticker or "").strip().upper()
    if not base_ticker:
        return None, None, None, None

    used, df = fetch_prices_with_suffixes(base_ticker)
    if used is None or df is None or df.empty:
        logger.info("Ticker %s nicht gefunden oder keine Daten", base_ticker)
        return None, None, None, None

    custom_universe = list(dict.fromkeys([*etf_universe, used]))
    prices_multi = load_raw_prices_for_universe(custom_universe)

    # Prüfe, ob der verwendete Ticker in prices_multi geladen wurde
    try:
        tickers_loaded = list(prices_multi.index.get_level_values("__ticker"))
    except Exception:
        logger.exception("Unexpected structure in prices_multi for %s", used)
        return used, None, None, prices_multi

    if used not in tickers_loaded:
        logger.warning("Ticker %s nicht in geladenen Preisen. Geladene Ticker: %s", used, sorted(set(tickers_loaded)))
        return used, None, None, prices_multi

    try:
        close_series = prices_multi.xs(used, level="__ticker")["Close"]
    except KeyError:
        logger.exception("Keine 'Close'-Spalte für %s in prices_multi", used)
        return used, None, None, prices_multi

    close_series = pd.to_numeric(close_series, errors="coerce").dropna()
    if close_series.empty:
        logger.warning("Close-Serie für %s ist leer nach Konvertierung", used)
        return used, None, None, prices_multi

    try:
        metrics = compute_metrics(close_series)
    except Exception as e:
        logger.exception("Fehler beim Berechnen der Kennzahlen für %s: %s", used, e)
        return used, close_series, None, prices_multi

    return used, close_series, metrics, prices_multi