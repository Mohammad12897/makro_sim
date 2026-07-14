# risk_dashboard/core/analysis.py
import numpy as np
from typing import Tuple, Optional, List
import pandas as pd
import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Lokale Importe hier, um zirkuläre Abhängigkeiten zu vermeiden
from risk_dashboard.core.data_loader import (
    fetch_prices_quiet,    
    load_raw_prices_for_universe,
    filter_valid_tickers
)
from scripts.ticker_cache import validate_ticker_with_cache


@st.cache_data
def compute_metrics(close_series: pd.Series, trading_days: int = 252, rf: float = 0.0) -> dict:
    """Berechnet Risiko- und Performancekennzahlen für eine Preisserie."""
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


def analyze_ticker(base_ticker: str, etf_universe: List[str]) -> Tuple[
    Optional[str], Optional[pd.Series], Optional[dict], Optional[pd.DataFrame]
]:
    """Lädt Daten für einen Ticker, berechnet Kennzahlen und erweitert das Universe."""
    base_ticker = (base_ticker or "").strip().upper()
    if not base_ticker:
        return None, None, None, None

    # Cache-Validator
    if not validate_ticker_with_cache(base_ticker):
        logger.warning("Ticker %s ist ungültig (Cache) – wird verworfen.", base_ticker)
        return None, None, None, None

    used, df = fetch_prices_quiet(base_ticker)
    if used is None or df is None or df.empty:
        logger.info("Ticker %s nicht gefunden oder keine Daten", base_ticker)
        return None, None, None, None

    # Universe erweitern
    custom_universe = list(dict.fromkeys([*(etf_universe or []), used]))
    custom_universe = [t.strip().upper() for t in custom_universe if isinstance(t, str) and t.strip()]
    custom_universe = list(dict.fromkeys(custom_universe))
    custom_universe = filter_valid_tickers(custom_universe)

    logger.info("Erweitertes, gefiltertes Universe: %s", custom_universe)

    try:
        prices_multi, skipped = load_raw_prices_for_universe(custom_universe)
    except Exception as e:
        logger.exception("Fehler beim Laden des erweiterten Universe für %s: %s", used, e)
        return used, None, None, None

    if skipped:
        logger.warning("Diese Ticker wurden entfernt, da sie keine Daten liefern: %s", skipped)

    # Prüfe Struktur
    try:
        #tickers_loaded = list(prices_multi.index.get_level_values("__ticker"))

        # Robust: MultiIndex oder SingleIndex akzeptieren
        if isinstance(prices_multi.index, pd.MultiIndex):
            if "__ticker" in prices_multi.index.names:
                tickers_loaded = list(prices_multi.index.get_level_values("__ticker"))
            else:
                # Fallback: nehme den ersten Level
                tickers_loaded = list(prices_multi.index.get_level_values(0))
        else:
            # SingleIndex: Index enthält direkt die Ticker
            tickers_loaded = list(prices_multi.index)

        tickers_loaded_unique = set(tickers_loaded)
    except Exception:
        logger.exception("Unexpected structure in prices_multi for %s", used)
        return used, None, None, prices_multi

    if used not in tickers_loaded_unique:
        logger.warning("Ticker %s nicht in geladenen Preisen. Geladene Ticker: %s",
                       used, sorted(tickers_loaded_unique))
        return used, None, None, prices_multi

    try:
        close_series = prices_multi.xs(used, level="__ticker")["Close"]
    except Exception:
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
