# scripts/yf_helper.py
# python scripts/yf_helper.py
import time
import random
import threading
from datetime import datetime as dt
from typing import Optional, List
from pathlib import Path
import pytz
import yfinance as yf
import pandas as pd
import logging
from io import StringIO

logger = logging.getLogger(__name__)

# Config
TZ = "Europe/Berlin"
# Config (oben)
RATE_INTERVAL = 2.0  # Sekunden zwischen Requests (erhöht)
BASE_SLEEP = 1.0
RETRIES = 5

# In wait_for_rate_slot() unverändert, aber exportiere die Funktion (def wait_for_rate_slot(): ...)

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 24 * 3600

# Rate limiter (global, thread-safe)
_last_request = 0.0
_lock = threading.Lock()


def _safe_read_csv_text(text: str) -> pd.DataFrame:
    if not text or "<html" in text.lower() or text.strip().count("\n") < 3:
        raise ValueError("Fallback returned invalid CSV/HTML")
    return pd.read_csv(StringIO(text), parse_dates=True, index_col=0)

def wait_for_rate_slot():
    global _last_request
    with _lock:
        now = time.time()
        wait = RATE_INTERVAL - (now - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()

def _tz_range():
    tz = pytz.timezone(TZ)
    start = tz.localize(dt(2018, 1, 1))
    end = tz.localize(dt.now())
    return start, end

def _ensure_date_fx_columns(df: pd.DataFrame, price_col: str) -> pd.DataFrame:
    """
    Liefert ein DataFrame mit Spalten ['date','fx'].
    Erwartet: df hat einen DatetimeIndex oder eine Datums-Spalte.
    """
    # Wenn Index Datum ist, resetten und umbenennen
    if isinstance(df.index, pd.DatetimeIndex):
        out = df.reset_index()
        date_col = out.columns[0]
    else:
        out = df.copy()
        # Falls es eine Spalte 'date' gibt, nutze sie, sonst versuche Index zu verwenden
        if "date" in out.columns:
            date_col = "date"
        else:
            out = out.reset_index()
            date_col = out.columns[0]

    # Stelle sicher, dass price_col existiert
    if price_col not in out.columns:
        # Fallback: wähle erste numerische Spalte
        numeric = out.select_dtypes(include="number").columns.tolist()
        if not numeric:
            return pd.DataFrame(columns=["date", "fx"])
        price_col = numeric[0]

    out = out.rename(columns={date_col: "date", price_col: "fx"})
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out[["date", "fx"]]
    out = out.dropna(subset=["date", "fx"])
    out = out.sort_values("date").reset_index(drop=True)
    return out


def download_one_with_backoff(ticker: str) -> Optional[pd.DataFrame]:
    start, end = _tz_range()

    # --- Cache read (sofort, vor Netzwerk)
    cache_path = CACHE_DIR / f"{ticker.replace('/', '_')}.parquet"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < CACHE_TTL_SECONDS:
        try:
            df = pd.read_parquet(cache_path)
            logger.info("Loaded %s from cache", ticker)
            if df is not None and not df.empty:
                df = df.sort_index()
                return df
        except Exception:
            logger.debug("Cache read failed for %s, continuing to download", ticker)
    # --- Ende Cache read

    for attempt in range(1, RETRIES + 1):
        try:
            wait_for_rate_slot()
            logger.debug("Attempt %d history() for %s", attempt, ticker)
            t = yf.Ticker(ticker)
            df = t.history(start=start, end=end, auto_adjust=True)
            if df is not None and not df.empty:
                logger.info("history() successful for %s (%d rows)", ticker, len(df))
                df = df.sort_index()
                try:
                    df.to_parquet(cache_path)
                except Exception:
                    logger.debug("Could not write cache for %s", ticker)
                return df
            logger.debug("history() returned empty for %s (attempt %d)", ticker, attempt)
        except Exception as e:
            if "Rate limited" in str(e) or type(e).__name__ == "YFRateLimitError":
                logger.warning("YFRateLimitError for %s: %s", ticker, e)
            else:
                logger.warning("history() Exception for %s (attempt %d): %s", ticker, attempt, e)

        # Backoff + jitter
        sleep = BASE_SLEEP * (2 ** (attempt - 1))
        sleep *= (0.6 + 0.8 * random.random())
        sleep = min(sleep, 60)
        logger.debug("Sleeping %.2fs before next attempt for %s", sleep, ticker)
        time.sleep(sleep)

    # Fallback: yf.download (single ticker)
    try:
        wait_for_rate_slot()
        logger.info("Fallback: yf.download() for %s", ticker)
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df is not None and not df.empty:
            logger.info("yf.download() successful for %s (%d rows)", ticker, len(df))
            try:
                df.to_parquet(cache_path)
            except Exception:
                logger.debug("Could not write cache for %s", ticker)
            return df
        logger.debug("yf.download() returned empty for %s", ticker)
    except Exception as e:
        if "Rate limited" in str(e) or type(e).__name__ == "YFRateLimitError":
            logger.warning("YFRateLimitError for %s: %s", ticker, e)
        else:
            logger.warning("Fallback download Exception for %s: %s", ticker, e)

    return None

def download_batch_with_backoff(tickers: List[str]) -> pd.DataFrame:
    start, end = _tz_range()
    tickers = [t for t in tickers if t]
    if not tickers:
        return pd.DataFrame()

    for attempt in range(1, RETRIES + 1):
        try:
            wait_for_rate_slot()
            logger.info("Batch download attempt %d for %d tickers", attempt, len(tickers))
            df = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                logger.info("Batch download successful (%s rows)", getattr(df, "shape", None))
                return df
            logger.debug("Batch download empty (attempt %d)", attempt)
        except Exception as e:
            # explizit RateLimit loggen
            if "Rate limited" in str(e) or type(e).__name__ == "YFRateLimitError":
                logger.warning("YFRateLimitError for batch %s: %s", tickers, e)
            else:
                logger.warning("Batch download Exception for %s (attempt %d): %s", tickers, attempt, e)

        # Backoff + jitter
        sleep = BASE_SLEEP * (2 ** (attempt - 1))
        sleep *= (0.6 + 0.8 * random.random())
        sleep = min(sleep, 60)
        logger.debug("Sleeping %.2fs before next batch attempt", sleep)
        time.sleep(sleep)

    return pd.DataFrame()
