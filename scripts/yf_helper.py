# scripts/yf_helper.py
import time
import random
import threading
import logging
from typing import List, Optional
from pathlib import Path
import io

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Config
RATE_INTERVAL = 2.0
BASE_SLEEP = 1.0
RETRIES = 5

# Cache
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 24 * 3600

# Rate limiter (global, thread-safe)
_last_request = 0.0
_lock = threading.Lock()

def wait_for_rate_slot():
    """Einfacher, thread-sicherer Rate-Limiter."""
    global _last_request
    with _lock:
        now = time.time()
        elapsed = now - _last_request
        if elapsed < RATE_INTERVAL:
            to_sleep = RATE_INTERVAL - elapsed + random.uniform(0.05, 0.2)
            time.sleep(to_sleep)
        _last_request = time.time()

def download_one_with_backoff(ticker: str, period: str = "max", retries: int = RETRIES, pause: float = BASE_SLEEP) -> Optional[pd.DataFrame]:
    """Lädt historische Preise für einen einzelnen Ticker mit Backoff, Cache und Fallback."""
    if not ticker:
        return None

    cache_path = CACHE_DIR / f"{ticker.replace('/', '_')}.parquet"
    try:
        if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < CACHE_TTL_SECONDS:
            df = pd.read_parquet(cache_path)
            if df is not None and not df.empty:
                df = df.sort_index()
                logger.info("Loaded %s from cache", ticker)
                return df
    except Exception:
        logger.debug("Cache read failed for %s, continuing to download", ticker)

    for attempt in range(1, retries + 1):
        try:
            wait_for_rate_slot()
            logger.debug("Attempt %d history() for %s", attempt, ticker)
            t = yf.Ticker(ticker)
            df = t.history(period=period, auto_adjust=False)
            if df is None or (hasattr(df, "empty") and df.empty):
                logger.warning("No data returned for %s on attempt %d", ticker, attempt)
                time.sleep(pause * (1 + attempt * 0.5))
                continue

            try:
                if hasattr(df.index, "tz") and df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
            except Exception:
                logger.debug("Could not tz_localize index for %s", ticker)

            df = df.sort_index()
            try:
                df.to_parquet(cache_path)
            except Exception:
                logger.debug("Could not write cache for %s", ticker)
            logger.info("history() successful for %s (%d rows)", ticker, len(df))
            return df

        except Exception as e:
            logger.warning("history() Exception for %s (attempt %d): %s", ticker, attempt, e)

        sleep = pause * (2 ** (attempt - 1))
        sleep *= (0.6 + 0.8 * random.random())
        sleep = min(sleep, 60)
        logger.debug("Sleeping %.2fs before next attempt for %s", sleep, ticker)
        time.sleep(sleep)

    # Fallback: yf.download single ticker
    try:
        wait_for_rate_slot()
        logger.info("Fallback: yf.download() for %s", ticker)
        df = yf.download(ticker, period=period, auto_adjust=False, progress=False)
        if df is not None and not df.empty:
            try:
                df.to_parquet(cache_path)
            except Exception:
                logger.debug("Could not write cache for %s", ticker)
            return df
    except Exception as e:
        logger.warning("Fallback download Exception for %s: %s", ticker, e)

    return None

def download_batch_with_backoff(tickers: List[str], period: str = "max", retries: int = 2, pause: float = BASE_SLEEP) -> Optional[pd.DataFrame]:
    """Versucht Batch-Download via yf.download. Bei Fehlschlag None zurückgeben."""
    tickers = [t for t in (tickers or []) if t]
    if not tickers:
        return pd.DataFrame()

    for attempt in range(1, retries + 1):
        try:
            wait_for_rate_slot()
            logger.info("Batch download attempt %d for %d tickers", attempt, len(tickers))
            df = yf.download(tickers, period=period, group_by='ticker', threads=True, progress=False, auto_adjust=False)
            if df is None:
                logger.warning("Batch download returned None for %s", tickers)
                time.sleep(pause * (1 + attempt * 0.5))
                continue

            if isinstance(df, pd.DataFrame):
                df = df.dropna(how="all", axis=1)
                if df.empty:
                    logger.warning("After dropna no valid series for %s", tickers)
                    time.sleep(pause * (1 + attempt * 0.5))
                    continue

            try:
                if hasattr(df.index, "tz") and df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
            except Exception:
                logger.debug("Could not tz_localize index for batch %s", tickers)

            logger.info("Batch download successful for %d tickers", len(tickers))
            return df

        except Exception as e:
            logger.warning("Batch download Exception for %s (attempt %d): %s", tickers, attempt, e)

        sleep = pause * (2 ** (attempt - 1))
        sleep *= (0.6 + 0.8 * random.random())
        sleep = min(sleep, 60)
        logger.debug("Sleeping %.2fs before next batch attempt", sleep)
        time.sleep(sleep)

    return None

def _safe_read_csv_text(text_or_bytes) -> Optional[pd.DataFrame]:
    """Robustes Lesen von CSV/TSV-Text (bytes oder str)."""
    if text_or_bytes is None:
        return None
    try:
        import chardet
        detector = True
    except Exception:
        detector = False

    if isinstance(text_or_bytes, (bytes, bytearray)):
        if detector:
            enc = chardet.detect(bytes(text_or_bytes)).get("encoding", "utf-8")
        else:
            try:
                text_or_bytes.decode("utf-8")
                enc = "utf-8"
            except Exception:
                enc = "latin-1"
        try:
            text = text_or_bytes.decode(enc, errors="replace")
        except Exception:
            text = text_or_bytes.decode("utf-8", errors="replace")
    else:
        text = str(text_or_bytes)

    sample = text[:8192]
    candidates = [";", ",", "\t", "|"]
    sep = max(candidates, key=lambda c: sample.count(c))
    if sample.count(sep) == 0:
        sep = ","

    import io
    for s in (sep, ",", ";", "\t"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=s, engine="python", skipinitialspace=True)
            # Debug: zeigt dir, was wirklich eingelesen wurde
            logger.debug(
                "read df shape=%s columns=%s sample=%s",
                getattr(df, 'shape', None),
                list(df.columns),
                df.head().to_dict(orient='records')[:3]
            )
            if df is not None and not df.empty:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            continue

    try:
        df = pd.read_table(io.StringIO(text), engine="python")
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass

    return None
