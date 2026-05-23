# risk_dashboard/core/data_loader.py
from typing import List, Tuple, Dict, Optional
from yfinance import download
import pandas as pd
import numpy as np
import yfinance as yf
import logging
import time
import concurrent.futures
import streamlit as st


logger = logging.getLogger(__name__)
SUFFIXES = ["", ".DE", ".MI", ".L", ".US", ".AX"]

@st.cache_data(ttl=3600)
def fetch_prices_with_suffixes(base: str, period: str = "max", auto_adjust: bool = False) -> Tuple[Optional[str], Optional[pd.DataFrame]]:
    """
    Versucht mehrere Suffixe und gibt (verwendeter_ticker, df) zurück.
    df hat Spalten Open, High, Low, Close, Volume und eine Hilfsspalte '__ticker'.
    """
    base = (base or "").strip().upper()
    if not base:
        return None, None

    for s in SUFFIXES:
        t = base + s
        try:
            ticker = yf.Ticker(t)

            # --- timezone check ---
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                info = {}

            if not info.get("exchangeTimezoneName"):
                logger.debug("No timezone for %s (suffix %s) — skipping", base, s)
                continue

            # --- robust history fetch with fallbacks ---
            df = None
            try:
                df = ticker.history(period=period, auto_adjust=auto_adjust)
            except ValueError as ve:
                logger.debug("history ValueError for %s: %s. Falling back to 5d", t, ve)
                try:
                    df = ticker.history(period="5d", auto_adjust=auto_adjust)
                except Exception as e2:
                    logger.debug("Fallback history failed for %s: %s", t, e2)
                    df = None
            except Exception as e:
                # Versuch: falls history fehlschlägt, probiere yf.download als Fallback
                logger.debug("history fetch failed for %s: %s. Trying download fallback", t, e)
                try:
                    df = download(t, start="2018-01-01", progress=False)
                except Exception as e2:
                    logger.debug("download fallback failed for %s: %s", t, e2)
                    df = None

            # Wenn wir eine DataFrame bekommen, normalisieren und zurückgeben
            if df is not None and not df.empty:
                df = df.copy()
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("UTC").tz_localize(None)
                df["__ticker"] = t
                return t, df

        except Exception as e:
            logger.debug("yfinance error for %s: %s", t, e)
            time.sleep(0.1)
            continue

    return None, None        

def _fetch_one(args):
    return fetch_prices_with_suffixes(*args)

@st.cache_data(ttl=3600)
def load_raw_prices_for_universe(universe: List[str], period: str = "max", auto_adjust: bool = False, max_workers: int = 6) -> Tuple[pd.DataFrame, List[str]]:
    """
    Lädt Preise für eine Liste von Basis-Tickern (ohne Suffix).
    Rückgabe: (DataFrame mit MultiIndex (Date, __ticker), Liste der übersprungenen Basis-Ticker)
    """
    # Normalisieren und deduplizieren
    bases = list(dict.fromkeys([b.strip().upper() for b in universe if isinstance(b, str) and b.strip()]))
    if not bases:
        cols = ["Open", "High", "Low", "Close", "Volume", "__ticker"]
        return pd.DataFrame(columns=cols), []

    results = []
    skipped: List[str] = []
    max_workers = min(max_workers, len(bases))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one, (b, period, auto_adjust)): b for b in bases}
        for fut in concurrent.futures.as_completed(futures):
            base = futures[fut]
            try:
                used_ticker, df = fut.result()
                if used_ticker and df is not None and not df.empty:
                    results.append(df)
                else:
                    logger.warning("No data for base %s with any suffixes", base)
                    skipped.append(base)
            except Exception as e:
                logger.exception("Error fetching %s: %s", base, e)
                skipped.append(base)

    if not results:
        cols = ["Open", "High", "Low", "Close", "Volume", "__ticker"]
        return pd.DataFrame(columns=cols), skipped

    combined = pd.concat(results)
    combined.index = pd.to_datetime(combined.index)
    combined = combined.sort_index()
    combined = combined.reset_index().rename(columns={"index": "Date"})
    combined = combined.set_index(["Date", "__ticker"]).sort_index()
    return combined, skipped

def try_download_with_alternatives(ticker_base: str, start: str = None, end: str = None) -> Tuple[str, pd.Series]:
    for s in SUFFIXES:
        t = ticker_base + s
        try:
            df = download(t, start=start, end=end, progress=False)
            if df is not None and not df.empty:
                col = "Adj Close" if "Adj Close" in df.columns else df.columns[-1]
                srs = df[col].rename(t)
                srs.index = pd.to_datetime(srs.index)
                logger.info("Download success for %s -> %s", ticker_base, t)
                return t, srs
        except Exception as e:
            logger.debug("Download failed for %s (tried %s): %s", ticker_base, t, e)
            continue
    logger.warning("No data for ticker base %s with any suffixes", ticker_base)
    return None, pd.Series(dtype=float)

def fetch_prices(tickers: List[str], start: str = "2018-01-01", end: str = None) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {}
    for tbase in tickers:
        # 1) try exact ticker first
        try:
            df = download(tbase, start=start, end=end, progress=False)
            if df is not None and not df.empty:
                col = "Adj Close" if "Adj Close" in df.columns else df.columns[-1]
                srs = df[col].rename(tbase)
                srs.index = pd.to_datetime(srs.index)
                out[tbase] = srs
                continue
        except Exception:
            pass

        # 2) try alternatives
        success_ticker, series = try_download_with_alternatives(tbase, start=start, end=end)
        if success_ticker is not None and not series.empty:
            out[success_ticker] = series
        else:
            out[tbase] = pd.Series(dtype=float)  # placeholder for missing
    return out





