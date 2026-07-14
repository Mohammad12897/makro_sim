# risk_dashboard/core/data_loader.py
"""
risk_dashboard.core.data_loader

Enthält:
- filter_valid_tickers (Cache-basiert)
- load_raw_prices_for_universe (robuster Batch-Loader mit Fallbacks)
- fetch_prices_quiet (Suffix-Fallback für einen Basis-Ticker)

Erwartete externe Hilfsfunktionen (aus scripts/yf_helper.py):
- download_batch_with_backoff(batch: List[str]) -> pd.DataFrame | None
- download_one_with_backoff(ticker: str) -> pd.DataFrame | None
- wait_for_rate_slot() -> None
Diese müssen in deinem Projekt vorhanden sein.
"""

from typing import List, Tuple, Optional
from pathlib import Path
import logging
import time
import random
import pandas as pd

# Externe Helfer (sollten in scripts/yf_helper.py existieren)
from scripts.yf_helper import (
    download_batch_with_backoff,
    download_one_with_backoff,
    wait_for_rate_slot,
)

# Cache-Validator (wie zuvor vorgeschlagen)
from scripts.ticker_cache import validate_ticker_with_cache

logger = logging.getLogger(__name__)


def filter_valid_tickers(tickers: List[str]) -> List[str]:
    """
    Entfernt ungültige / delistete Ticker aus der Liste.
    Nutzt validate_ticker_with_cache (persistenter Cache, TTL konfigurierbar).
    """
    valid: List[str] = []
    for t in tickers:
        t_norm = (t or "").strip().upper()
        if not t_norm:
            continue
        try:
            if validate_ticker_with_cache(t_norm):
                valid.append(t_norm)
            else:
                logger.warning("Ticker %s ist ungültig oder liefert keine Daten – wird entfernt.", t_norm)
        except Exception:
            logger.exception("Fehler bei Validierung von Ticker %s; wird entfernt.", t_norm)
    # deduplizieren und Reihenfolge bewahren
    return list(dict.fromkeys(valid))


import sys
import os
import contextlib
import io
import yfinance as yf
import streamlit as st

# --- Kontextmanager: stdout/stderr temporär stummschalten ---
@contextlib.contextmanager
def suppress_stdout_stderr():
    """
    Temporarily suppress stdout and stderr (works for C-level prints too).
    Use with: with suppress_stdout_stderr(): ...
    """
    # Save file descriptors
    try:
        devnull = os.open(os.devnull, os.O_RDWR)
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        yield
    finally:
        # Restore original fds
        os.dup2(old_stdout_fd, 1)
        os.dup2(old_stderr_fd, 2)
        os.close(old_stdout_fd)
        os.close(old_stderr_fd)

# --- Quiet fetch wrapper mit optionalem Caching ---
@st.cache_data(ttl=60*60)  # optional: 1 Stunde cache; anpassen oder entfernen
def fetch_prices_quiet(tickers: List[str],
                       start: Optional[str] = None,
                       end: Optional[str] = None,
                       interval: str = "1d") -> pd.DataFrame:
    """
    Lade Preisdaten für tickers, unterdrückt yfinance prints.
    Gibt ein DataFrame zurück mit MultiIndex columns oder mindestens einer 'close' Spalte.
    Wenn mehrere Ticker, versucht DataFrame mit close-Spalten pro Ticker zu liefern.
    """
    # 1) Versuche vorhandene Projektfunktion zu nutzen (falls vorhanden)
    try:
        # Wenn du eine projektweite Funktion fetch_prices_quiet hast, nutze sie
        from risk_dashboard.core.data_loader import fetch_prices_quiet as project_fetch
    except Exception:
        project_fetch = None

    # 2) Führe den Download innerhalb des suppress-Kontexts aus
    try:
        with suppress_stdout_stderr():
            if project_fetch is not None:
                # project_fetch erwartet evtl. eine Liste und liefert DataFrame mit 'close'
                df = project_fetch(tickers)
            else:
                # Fallback: yfinance.download
                # yfinance.download returns a DataFrame with columns like ('Close', 'Adj Close', ...)
                df = yf.download(tickers, start=start, end=end, interval=interval, group_by='ticker', threads=True, progress=False)
    except Exception as e:
        # Fehler beim Laden: gib leeres DF zurück und logge in Streamlit
        st.warning(f"Fehler beim Laden der Preise für {tickers}: {e}")
        return pd.DataFrame()

    # 3) Normalisiere das Ergebnis: Ziel ist eine Series/DataFrame mit 'close'
    # Falls project_fetch bereits das gewünschte Format liefert, gib es zurück
    if isinstance(df, pd.DataFrame):
        # yfinance single ticker: columns like ['Open','High','Low','Close','Adj Close','Volume']
        # yfinance multi ticker: top-level columns are tickers
        # Ziel: DataFrame mit einer 'close' Spalte pro Ticker (oder Series für Einzelticker)
        try:
            # Wenn MultiIndex (ticker, field)
            if isinstance(df.columns, pd.MultiIndex):
                # Extrahiere Close/close/Close-Spalte für jeden Ticker
                close_frames = {}
                for t in tickers:
                    # tolerant gegenüber verschiedenen Feldnamen
                    for field in ("Close", "close", "Adj Close", "AdjClose"):
                        if (t, field) in df.columns:
                            close_frames[t] = df[(t, field)].rename(t)
                            break
                if close_frames:
                    return pd.concat(close_frames, axis=1)
            else:
                # Single ticker oder single-level columns
                # Versuche 'Close' oder 'close' Spalte
                if "Close" in df.columns:
                    return pd.DataFrame({"close": df["Close"]})
                if "close" in df.columns:
                    return pd.DataFrame({"close": df["close"]})
                # Falls project_fetch lieferte bereits 'close' als Spalte
                if "close" in df.columns:
                    return df
        except Exception:
            pass

    # Fallback: wenn df nicht wie erwartet, versuche es zu konvertieren
    try:
        # Wenn df ist Series (ein Ticker)
        if isinstance(df, pd.Series):
            return pd.DataFrame({"close": df})
    except Exception:
        pass

    # Letzter Fallback: leeres DF
    return pd.DataFrame()


def load_raw_prices_for_universe(universe: List[str],
                                 period: str = "max",
                                 auto_adjust: bool = False,
                                 max_workers: int = 2) -> Tuple[pd.DataFrame, List[str]]:
    """
    Lädt historische Preise für eine Liste von Basis-Tickern (Universe).
    Rückgabe: (combined_df, skipped_list)
    - combined_df: DataFrame mit MultiIndex (Date, __ticker) und Spalten Open/High/Low/Close/Volume
    - skipped_list: Liste der Ticker, die keine Daten liefern
    """

    # Normalisiere und dedupliziere Basen
    bases = list(dict.fromkeys([b.strip().upper() for b in (universe or []) if isinstance(b, str) and b.strip()]))
    if not bases:
        cols = ["Open", "High", "Low", "Close", "Volume", "__ticker"]
        return pd.DataFrame(columns=cols), []

    # Filtere bereits hier mit Cache
    bases = filter_valid_tickers(bases)
    logger.info("Gültige Ticker nach Cache-Filter: %s", bases)
    if not bases:
        cols = ["Open", "High", "Low", "Close", "Volume", "__ticker"]
        return pd.DataFrame(columns=cols), list(dict.fromkeys(universe or []))

    results: List[pd.DataFrame] = []
    skipped: List[str] = []

    batch_size = 4
    batches = [bases[i:i + batch_size] for i in range(0, len(bases), batch_size)]

    for batch in batches:
        # Normalisiere und filtere die aktuelle Batch
        batch = list(dict.fromkeys([b.strip().upper() for b in batch if isinstance(b, str) and b.strip()]))
        batch = filter_valid_tickers(batch)
        logger.info("Gültige Ticker in dieser Batch nach Cache-Filter: %s", batch)

        if not batch:
            logger.info("Keine gültigen Ticker in dieser Batch, überspringe.")
            continue

        try:
            # globaler rate slot vor Batch
            wait_for_rate_slot()

            df_batch = download_batch_with_backoff(batch)

            if df_batch is None or df_batch.empty:
                # serieller Fallback pro Ticker
                for t in batch:
                    wait_for_rate_slot()

                    # Einzel-Ticker prüfen (Cache)
                    try:
                        if not validate_ticker_with_cache(t):
                            skipped.append(t)
                            logger.warning("Ticker %s ist ungültig (Cache) – wird übersprungen.", t)
                            continue
                    except Exception:
                        logger.debug("Cache-Check für %s schlug fehl; versuche Download.", t)

                    df_one = None
                    try:
                        df_one = download_one_with_backoff(t)
                    except Exception as e:
                        logger.debug("download_one_with_backoff für %s warf: %s", t, e)
                        df_one = None

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
                # Robust handling for single-level df_batch (infer tickers from column names)
                if isinstance(df_batch.columns, pd.MultiIndex):
                    tickers = list(dict.fromkeys(df_batch.columns.get_level_values(1)))
                    tickers = filter_valid_tickers([t.strip().upper() for t in tickers])
                    for ticker in tickers:
                        try:
                            sub = df_batch.xs(ticker, axis=1, level=1, drop_level=False).copy()
                        except Exception:
                            # fallback: try to select columns that contain ticker as suffix/prefix
                            cols = [c for c in df_batch.columns if ticker in str(c)]
                            sub = df_batch[cols].copy() if cols else pd.DataFrame()
                        if sub.empty:
                            skipped.append(ticker)
                            continue
                        if isinstance(sub.columns, pd.MultiIndex):
                            sub.columns = [c[0] for c in sub.columns]
                        sub["__ticker"] = ticker
                        sub.index = pd.to_datetime(sub.index, errors="coerce")
                        sub = sub.reset_index().rename(columns={sub.index.name or "index": "Date"})
                        sub = sub.set_index(["Date", "__ticker"])
                        results.append(sub)
                else:
                    # Single-level columns: infer ticker per column
                    for col in df_batch.columns:
                        series = df_batch[col].dropna()
                        if series.empty:
                            continue
                        colname = str(col)
                        # heuristics to guess ticker
                        if "." in colname:
                            ticker_guess = colname.split(".")[-1]
                        elif " " in colname:
                            ticker_guess = colname.split()[-1]
                        else:
                            ticker_guess = colname
                        sub = pd.DataFrame(df_batch[col]).copy()
                        sub["__ticker"] = ticker_guess
                        sub.index = pd.to_datetime(sub.index, errors="coerce")
                        sub = sub.reset_index().rename(columns={sub.index.name or "index": "Date"})
                        sub = sub.set_index(["Date", "__ticker"])
                        results.append(sub)
        
        except Exception as e:
            logger.exception("Batch download failed for %s: %s", batch, e)
            # Falls Batch komplett fehlschlägt, markieren wir alle Batch-Ticker als skipped
            skipped.extend(batch)

        # Stagger zwischen Batches (freundlich zu API)
        time.sleep(1.0 + random.random() * 2.0)

    if results:
        combined = pd.concat(results, axis=0).sort_index()
    else:
        combined = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    valid_tickers = list(dict.fromkeys(bases))
    invalid_tickers = list(dict.fromkeys(skipped))

    logger.info("Final gültige Ticker: %s", valid_tickers)
    logger.info("Final ungültige Ticker: %s", invalid_tickers)

    return combined, invalid_tickers
