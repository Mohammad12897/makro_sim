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

from typing import List, Tuple, Optional , Union
from pathlib import Path
import logging
from datetime import date
import threading
import time
import random
import pandas as pd
import yfinance as yf
import sys
import os
import contextlib
import io
import streamlit as st
import re

logger = logging.getLogger(__name__)


from risk_dashboard.core.safety import DUMP_MARKERS  # Liste der Marker, zentral verwaltet

from risk_dashboard.data_utils import flatten_yf_dataframe

# Externe Helfer (sollten in scripts/yf_helper.py existieren)
from risk_dashboard.core.yf_helper import (
    download_batch_with_backoff,
    download_one_with_backoff,
    wait_for_rate_slot,
)

# Cache-Validator (wie zuvor vorgeschlagen)
from risk_dashboard.core.ticker_cache import validate_ticker_with_cache


DEFAULT_START = "2016-01-01"
DEFAULT_END = date.today().isoformat()
YF_DOWNLOAD_TIMEOUT = 30  # Sekunden, anpassen
CHUNK_SIZE = 10  # Anzahl Ticker pro Request, anpassen


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

def _strip_edge_metadata_from_string(s: str, markers: List[str] = DUMP_MARKERS) -> str:
    if not s:
        return s.strip()
    if not markers:
        return s.strip()
    lower = s.lower()
    if not any((m and m.lower() in lower) for m in markers):
        return s.strip()

    cleaned = s
    # Entferne Zuweisungsblöcke wie: marker = [ ... ]
    try:
        escaped = [re.escape(m) for m in markers if m]
        if escaped:
            lhs = r"|".join(escaped)
            cleaned = re.sub(r"(?ms)\b(?:" + lhs + r")\s*=\s*\[.*?\]\s*", "", cleaned)
    except Exception:
        pass

    # Entferne unkommentierte Zeilen, die Marker enthalten
    try:
        marker_or = r"|".join([re.escape(m) for m in markers if m])
        cleaned = re.sub(r"(?im)^[ \t]*(?!#).*?(?:" + marker_or + r").*\r?\n?", "", cleaned)
    except Exception:
        pass

    # Generischer Tag-Stripper: <tag>...</tag> und einzelne opening tags
    cleaned = re.sub(r"(?ms)<[A-Za-z0-9_:-]+(?:\s+[^>]*)?>.*?</[A-Za-z0-9_:-]+>", "", cleaned)
    cleaned = re.sub(r"(?i)<[A-Za-z0-9_:-]+(?:\s+[^>]*)?>", "", cleaned)

    # Trim und leere Zeilen entfernen
    cleaned = "\n".join([ln for ln in (l.strip() for l in cleaned.splitlines()) if ln])
    return cleaned.strip()

def parse_tickers(raw: Union[str, List[str], tuple]) -> List[str]:
    """
    Bereinigt (falls Marker vorhanden), splittet und liefert Uppercase-Ticker ohne Duplikate.
    """
    if raw is None:
        return []

    # Wenn String: zuerst bereinigen, dann splitten
    if isinstance(raw, str):
        cleaned = _strip_edge_metadata_from_string(raw)
        parts = [p.strip() for p in re.split(r"[,\n;|]+", cleaned) if p.strip()]
    else:
        # Liste/Tuple: Elemente bereinigen/trimmen einzeln (keine Dump-Blöcke erwartet)
        parts = [str(t).strip() for t in raw if t and str(t).strip()]

    # Normalisiere und dedupe while preserving order
    seen = set()
    out: List[str] = []
    for p in parts:
        p_up = p.upper()
        if p_up not in seen:
            seen.add(p_up)
            out.append(p_up)
    return out


def _yf_download_with_timeout(tickers_list: List[str], yf_kwargs: dict, timeout: int = YF_DOWNLOAD_TIMEOUT):
    """
    Führt yf.download(**yf_kwargs) in einem Thread aus und wartet 'timeout' Sekunden.
    Gibt das raw-Resultat zurück oder None bei Timeout.
    Wenn yf.download eine Exception wirft, wird diese weitergereicht.
    """
    result = {"raw": None, "exc": None}

    def target():
        try:
            # yfinance erwartet entweder list oder string; hier übergeben wir list
            result["raw"] = yf.download(**yf_kwargs)
        except Exception as e:
            result["exc"] = e

    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive():
        logger.warning("yf.download timed out after %s seconds for %s", timeout, tickers_list)
        return None
    if result["exc"]:
        raise result["exc"]
    return result["raw"]

def _chunked(iterable: List[str], n: int):
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]

def _parse_tickers_input_old(raw):
    """
    Akzeptiert: List[str] oder String mit Komma/Semikolon/Zeilenumbruch getrennt.
    Liefert: Liste von Uppercase-Tickern ohne Duplikate.
    """
    import re
    if raw is None:
        return []
    if isinstance(raw, list):
        parts = [str(t).strip() for t in raw if t and str(t).strip()]
    else:
        parts = [p.strip() for p in re.split(r"[,\n;]+", str(raw)) if p.strip()]
    seen = set()
    out = []
    for p in parts:
        p_up = p.upper()
        if p_up not in seen:
            seen.add(p_up)
            out.append(p_up)
    return out

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
def fetch_prices_safe(
    tickers: Union[List[str], str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    auto_adjust: bool = False,
    threads: bool = True,
    retries: int = 2,
    return_removed: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, List[str]]]:
    """
    Lade Preisdaten für tickers; gibt flaches DataFrame zurück.
    - tickers: Liste oder String (Komma/Zeilenumbruch/; getrennt).
    - return_removed: wenn True, zusätzlich Liste der Ticker ohne Daten zurückgeben.
    """
    # sichere Defaults
    start = start or DEFAULT_START
    end = end or DEFAULT_END

    # 1) robustes Parsen der Eingabe (parse_tickers muss vorhanden sein)
    tickers_list = parse_tickers(tickers)
    if not tickers_list:
        if return_removed:
            return pd.DataFrame(), []
        return pd.DataFrame()

    # 2) Download in Chunks mit Retries und Timeout
    all_raws = []
    last_exc = None
    for chunk in _chunked(tickers_list, CHUNK_SIZE):
        # prepare kwargs for this chunk
        yf_kwargs = dict(
            tickers=chunk,
            start=start,
            end=end,
            interval=interval,
            group_by="ticker",
            auto_adjust=auto_adjust,
            threads=threads,
            progress=False,
        )

        raw_chunk = None
        for attempt in range(retries + 1):
            try:
                raw_chunk = _yf_download_with_timeout(chunk, yf_kwargs, timeout=YF_DOWNLOAD_TIMEOUT)
                # Wenn Timeout (None) -> raise to trigger retry logic
                if raw_chunk is None:
                    raise TimeoutError(f"yf.download timed out for chunk {chunk}")
                break
            except Exception as e:
                last_exc = e
                logger.exception("yfinance download failed (attempt %s) for %s: %s", attempt, chunk, e)
                if attempt < retries:
                    time.sleep(2 ** attempt)
        if raw_chunk is None:
            # Alle Versuche für diesen Chunk fehlgeschlagen
            logger.warning("All attempts failed for chunk %s", chunk)
            # Wir fahren mit den anderen Chunks fort, aber merken uns die fehlenden Ticker
            all_raws.append((chunk, None))
        else:
            all_raws.append((chunk, raw_chunk))

    # Wenn kein erfolgreicher Chunk
    if not any(raw is not None for _, raw in all_raws):
        logger.warning("fetch_prices_safe: all attempts failed for all chunks for %s", tickers_list)
        if return_removed:
            return pd.DataFrame(), tickers_list
        return pd.DataFrame()

    # 3) Flatten / Merge der Chunk-Resultate
    dfs = []
    for chunk, raw in all_raws:
        if raw is None:
            continue
        try:
            df_chunk = flatten_yf_dataframe(raw)
        except Exception:
            try:
                df_chunk = pd.DataFrame(raw)
            except Exception:
                logger.exception("Failed to flatten yfinance chunk for %s", chunk)
                continue
        dfs.append(df_chunk)

    if not dfs:
        logger.warning("No dataframes produced from yfinance results for %s", tickers_list)
        if return_removed:
            return pd.DataFrame(), tickers_list
        return pd.DataFrame()

    # Merge/concat auf Index (Datum); Spalten sollten unterschiedliche Ticker enthalten
    try:
        df = pd.concat(dfs, axis=1, join="outer")
    except Exception:
        # Fallback: nimm erstes DF
        df = dfs[0]

    # 4) Index in Datetime umwandeln
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    # 5) Bestimme Ticker ohne Daten
    removed: List[str] = []
    if isinstance(df.columns, pd.MultiIndex):
        top_level = list(dict.fromkeys([c[0] for c in df.columns]))
        for t in tickers_list:
            if t not in top_level:
                removed.append(t)
    else:
        for t in tickers_list:
            if t not in df.columns:
                removed.append(t)
            else:
                try:
                    if df[t].dropna().empty:
                        removed.append(t)
                except Exception:
                    removed.append(t)

    if removed:
        logger.warning("Removed tickers with no data: %s", removed)
        df = df.drop(columns=removed, errors="ignore")

    if return_removed:
        return df, removed
    return df


def fetch_prices_safe_old(
    tickers: Union[List[str], str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    auto_adjust: bool = False,
    threads: bool = True,
    retries: int = 2,
    return_removed: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, List[str]]]:
    """
    Lade Preisdaten für tickers; gibt flaches DataFrame zurück.
    - tickers: Liste oder String (Komma/Zeilenumbruch/; getrennt).
    - return_removed: wenn True, zusätzlich Liste der Ticker ohne Daten zurückgeben.
    """
    # setze Defaults wenn None
    start = start or DEFAULT_START
    end = end or DEFAULT_END

    # 1) robustes Parsen der Eingabe
    tickers_list = parse_tickers(tickers)
    if not tickers_list:
        if return_removed:
            return pd.DataFrame(), []
        return pd.DataFrame()

    # prepare kwargs for yf.download
    yf_kwargs = dict(
        tickers=tickers_list,
        start=start,
        end=end,
        interval=interval,
        group_by="ticker",
        auto_adjust=auto_adjust,
        threads=threads,
        progress=False,
    )

    # 2) Download mit Retries
    raw = None
    last_exc = None
    for attempt in range(retries + 1):
        try:
            raw = yf.download(
                tickers_list,
                start=start,
                end=end,
                interval=interval,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads,
                progress=False,
            )
            break
        except Exception as e:
            last_exc = e
            logger.exception("yfinance download failed (attempt %s) for %s: %s", attempt, tickers_list, e)
            if attempt < retries:
                import time
                time.sleep(2 ** attempt)

    if raw is None:
        logger.warning("fetch_prices_safe: all attempts failed for %s", tickers_list)
        if return_removed:
            return pd.DataFrame(), tickers_list
        return pd.DataFrame()

    # 3) Flatten / Fallbacks
    try:
        df = flatten_yf_dataframe(raw)
    except Exception:
        try:
            df = pd.DataFrame(raw)
        except Exception:
            logger.exception("Failed to flatten yfinance output for %s", tickers_list)
            if return_removed:
                return pd.DataFrame(), tickers_list
            return pd.DataFrame()

    # 4) Index in Datetime umwandeln
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    # 5) Bestimme Ticker ohne Daten
    removed: List[str] = []
    if isinstance(df.columns, pd.MultiIndex):
        top_level = list(dict.fromkeys([c[0] for c in df.columns]))
        for t in tickers_list:
            if t not in top_level:
                removed.append(t)
    else:
        for t in tickers_list:
            if t not in df.columns:
                removed.append(t)
            else:
                try:
                    if df[t].dropna().empty:
                        removed.append(t)
                except Exception:
                    removed.append(t)

    if removed:
        logger.warning("Removed tickers with no data: %s", removed)
        df = df.drop(columns=removed, errors="ignore")

    if return_removed:
        return df, removed
    return df

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