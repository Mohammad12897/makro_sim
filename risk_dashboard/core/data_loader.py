# risk_dashboard/core/data_loader.py
from typing import List, Tuple, Dict, Optional
from yfinance import download
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import logging
import time
import concurrent.futures
import streamlit as st
import random
import logging


# Versuche Import aus scripts; falls nicht vorhanden, Fallback (führe nur EINEN Importblock)
logger = logging.getLogger(__name__)
try:
    from scripts.yf_helper import download_batch_with_backoff, download_one_with_backoff, wait_for_rate_slot
except ModuleNotFoundError:
    # Fallback: add project root to sys.path and retry
    from pathlib import Path as _Path
    project_root = _Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        from scripts.yf_helper import download_batch_with_backoff, download_one_with_backoff, wait_for_rate_slot
    except Exception as e:
        logger.exception("Konnte scripts.yf_helper nicht importieren: %s", e)
        # minimaler fallback, damit App nicht abstürzt
        def download_one_with_backoff(ticker): 
            return None
        def download_batch_with_backoff(tickers):
            return pd.DataFrame()
        def wait_for_rate_slot():
            time.sleep(1.5)


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

def _fetch_one(base: str) -> Optional[pd.DataFrame]:
    """
    Lade Preise für einen Basis-Ticker mit Retries, Backoff und Fallback.
    Gibt ein DataFrame oder None zurück.
    """
    base = (base or "").strip().upper()
    if not base:
        return None

    try:
        wait_for_rate_slot()
        df = download_one_with_backoff(base)
    except Exception as e:
        logger.exception("Unexpected exception while downloading %s: %s", base, e)
        return None

    # kleine Pause, um Bursts zu vermeiden
    time.sleep(0.2 + random.random() * 0.4)

    if df is None or df.empty:
        logger.warning("No data for ticker base %s after retries/fallback", base)
        return None

    try:
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.sort_index()
    except Exception:
        logger.exception("Failed to normalize index for %s", base)
        return None

    return df

@st.cache_data(ttl=3600)
def load_raw_prices_for_universe(universe: List[str],
                                 period: str = "max",
                                 auto_adjust: bool = False,
                                 max_workers: int = 2) -> Tuple[pd.DataFrame, List[str]]:
    bases = list(dict.fromkeys([b.strip().upper() for b in universe if isinstance(b, str) and b.strip()]))
    if not bases:
        cols = ["Open", "High", "Low", "Close", "Volume", "__ticker"]
        return pd.DataFrame(columns=cols), []

    results = []
    skipped: List[str] = []

    batch_size = 4
    batches = [bases[i:i+batch_size] for i in range(0, len(bases), batch_size)]

    for batch in batches:
        try:
            # globaler rate slot vor Batch
            wait_for_rate_slot()
            df_batch = download_batch_with_backoff(batch)

            if df_batch is None or df_batch.empty:
                # serieller Fallback pro Ticker
                for t in batch:
                    wait_for_rate_slot()
                    df_one = download_one_with_backoff(t)
                    time.sleep(0.2 + random.random() * 0.4)
                    if df_one is None or df_one.empty:
                        skipped.append(t)
                        logger.warning("No data for ticker base %s after retries/fallback", t)
                        continue
                    if "__ticker" not in df_one.columns:
                        df_one = df_one.copy()
                        df_one["__ticker"] = t
                    if not isinstance(df_one.index, pd.DatetimeIndex):
                        df_one.index = pd.to_datetime(df_one.index, errors="coerce")
                    df_one = df_one.reset_index().rename(columns={df_one.index.name or "index": "Date"})
                    df_one = df_one.set_index(["Date", "__ticker"])
                    results.append(df_one)
            else:
                # MultiIndex-Spalten (typisch bei yf.download mit mehreren Tickers)
                if isinstance(df_batch.columns, pd.MultiIndex):
                    tickers = list(dict.fromkeys(df_batch.columns.get_level_values(1)))
                    for ticker in tickers:
                        try:
                            sub = df_batch.xs(ticker, axis=1, level=1, drop_level=False)
                        except Exception:
                            logger.debug("Could not xs for ticker %s in batch", ticker)
                            continue
                        sub = sub.copy()
                        if isinstance(sub.columns, pd.MultiIndex):
                            sub.columns = [c[0] for c in sub.columns]
                        sub["__ticker"] = ticker
                        sub.index = pd.to_datetime(sub.index, errors="coerce")
                        sub = sub.reset_index().rename(columns={sub.index.name or "index": "Date"})
                        sub = sub.set_index(["Date", "__ticker"])
                        results.append(sub)
                else:
                    # Single-level columns
                    if len(batch) == 1:
                        ticker = batch[0]
                        df = df_batch.copy()
                        if "__ticker" not in df.columns:
                            df["__ticker"] = ticker
                        df.index = pd.to_datetime(df.index, errors="coerce")
                        df = df.reset_index().rename(columns={df.index.name or "index": "Date"})
                        df = df.set_index(["Date", "__ticker"])
                        results.append(df)
                    else:
                        df = df_batch.copy()
                        df["__ticker"] = ",".join(batch)
                        df.index = pd.to_datetime(df.index, errors="coerce")
                        df = df.reset_index().rename(columns={df.index.name or "index": "Date"})
                        df = df.set_index(["Date", "__ticker"])
                        results.append(df)

        except Exception as e:
            logger.exception("Batch download failed for %s: %s", batch, e)
            skipped.extend(batch)

        # Stagger zwischen Batches
        time.sleep(1.0 + random.random() * 2.0)

    if results:
        combined = pd.concat(results, axis=0).sort_index()
    else:
        combined = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    return combined, list(dict.fromkeys(skipped))


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







