# risk_dashboard/data_utils.py
import time, random, logging
from typing import List, Optional, Any, Dict, Sequence, Tuple
import pandas as pd
import streamlit as st
import yfinance as yf
from requests.exceptions import RequestException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from risk_dashboard.config import DEFAULT_START_STR


@st.cache_data(ttl=3600)
def cached_download_prices(tickers, start, end, **kwargs):
    from risk_dashboard.core.etf_tools import download_prices
    return download_prices(tickers, start=start, end=end, **kwargs)

def flatten_yf_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Robust flatten yfinance output:
    - Prefer 'Adj Close' then 'Close'
    - Return DataFrame with uppercase column names (tickers)
    """
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        # (ticker, field) -> level 1 contains field names
        for label in ("Adj Close", "AdjClose", "Adj_Close", "Close"):
            try:
                if label in df.columns.get_level_values(1):
                    out = df.xs(label, axis=1, level=1, drop_level=True)
                    out.columns = [str(c).upper() for c in out.columns]
                    return out
            except Exception:
                continue

        # (field, ticker) -> level 0 contains field names
        for label in ("Adj Close", "AdjClose", "Adj_Close", "Close"):
            try:
                if label in df.columns.get_level_values(0):
                    out = df.xs(label, axis=1, level=0, drop_level=True)
                    out.columns = [str(c).upper() for c in out.columns]
                    return out
            except Exception:
                continue

        # Fallback: first numeric column per ticker
        cols = {}
        for lvl in (0, 1):
            try:
                tickers = list(dict.fromkeys(df.columns.get_level_values(lvl)))
                for t in tickers:
                    try:
                        sub = df.xs(t, axis=1, level=lvl, drop_level=True)
                    except Exception:
                        try:
                            sub = df[t]
                        except Exception:
                            sub = None
                    if sub is None:
                        continue
                    num = sub.select_dtypes(include="number")
                    if not num.empty:
                        cols[str(t).upper()] = num.iloc[:, 0]
                if cols:
                    return pd.DataFrame(cols)
            except Exception:
                continue

        # Last fallback: concat with unique names
        try:
            pieces = []
            names = []
            for a, b in df.columns:
                pieces.append(df[(a, b)])
                names.append(f"{str(a).upper()}_{str(b).upper()}")
            out = pd.concat(pieces, axis=1)
            out.columns = names
            return out
        except Exception:
            df.columns = [f"{c}" for c in df.columns]
            return df

    # single-level: uppercase and dedupe
    cols = list(df.columns)
    seen = {}
    new_cols = []
    for c in cols:
        key = str(c).upper()
        if key in seen:
            seen[key] += 1
            new_cols.append(f"{key}_{seen[key]}")
        else:
            seen[key] = 0
            new_cols.append(key)
    df.columns = new_cols
    return df

def _normalize_tickers(tickers: Sequence[str]) -> List[str]:
    return [t.strip().upper() for t in tickers if t and str(t).strip()]

def fetch_prices_from_yf(tickers, start=DEFAULT_START_STR, end=None,
                         interval: str = "1d", auto_adjust: bool = False,
                         threads: bool = False, **kwargs) -> pd.DataFrame:
    """
    Lädt Preise mit yfinance.download.
    - interval: '1d', '1wk', '1mo', ...
    - zusätzliche kwargs werden an yf.download weitergereicht
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return pd.DataFrame()

    logger.debug("fetch_prices_from_yf start tickers=%s start=%s end=%s interval=%s", tickers, start, end, interval)

    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            group_by="ticker",
            auto_adjust=auto_adjust,
            threads=threads,
            **kwargs
        )
    except Exception as e:
        logger.warning("fetch_prices_from_yf failed for %s: %s", tickers, e)
        return pd.DataFrame()

    if raw is None or raw.empty:
        logger.warning("fetch_prices_from_yf returned empty DataFrame for %s", tickers)
        return pd.DataFrame()

    df = flatten_yf_dataframe(raw)

    # Index bereinigen
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass
    df = df.sort_index()

    logger.debug("fetch_prices_from_yf returning dataframe with columns %s and index length %d",
                 list(df.columns), len(df.index))
    return df

def safe_fetch(
    tickers: List[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    retries: int = 2,
    backoff_factor: float = 0.5,
    timeout_seconds: int = 30,
    allow_empty: bool = False,
    cache: Optional[Dict[str, pd.DataFrame]] = None,
    cache_key: Optional[str] = None,
    raise_on_failure: bool = True,
    **fetch_kwargs: Any,
) -> pd.DataFrame:
    # Defaults im Body setzen (nicht in Signatur)
    start = start or DEFAULT_START_STR
    end = end or datetime.today().strftime("%Y-%m-%d")

    # Guard: leere Tickerliste
    if not tickers:
        logger.debug("safe_fetch: received empty tickers list")
        if allow_empty:
            return pd.DataFrame()
        raise ValueError("safe_fetch: tickers list is empty")

    # Cache lookup
    if cache is not None and cache_key is not None:
        cached = cache.get(cache_key)
        if cached is not None and not cached.empty:
            logger.debug("safe_fetch: returning cached data for %s", cache_key)
            return cached

    last_exc = None
    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        try:
            logger.debug(
                "safe_fetch: attempt %d/%d tickers=%s start=%s end=%s interval=%s kwargs=%s",
                attempt, attempts, tickers, start, end, interval,
                {k: fetch_kwargs.get(k) for k in ("auto_adjust","threads") if k in fetch_kwargs}
            )
            df = fetch_prices_from_yf(
                tickers,
                start=start,
                end=end,
                interval=interval,
                timeout=timeout_seconds,
                **fetch_kwargs
            )
            if df is not None and not df.empty:
                if cache is not None and cache_key is not None:
                    cache[cache_key] = df
                logger.debug("safe_fetch: success attempt %d rows=%d cols=%s", attempt, len(df.index), list(df.columns)[:10])
                return df
            logger.debug("safe_fetch: empty result on attempt %d for %s", attempt, tickers)
        except RequestException as re:
            last_exc = re
            logger.warning("safe_fetch: network error on attempt %d for %s: %s", attempt, tickers, re)
        except Exception as exc:
            last_exc = exc
            logger.exception("safe_fetch: unexpected error on attempt %d for %s", attempt, tickers)

        # backoff with jitter
        sleep_for = backoff_factor * (2 ** (attempt - 1))
        jitter = random.uniform(0, sleep_for * 0.1)
        total_sleep = sleep_for + jitter
        logger.debug("safe_fetch: sleeping %.2fs before next attempt", total_sleep)
        time.sleep(total_sleep)

    logger.error("safe_fetch: all attempts failed for %s", tickers)
    if allow_empty:
        return pd.DataFrame()
    if raise_on_failure:
        raise RuntimeError(f"safe_fetch: failed to fetch prices for {tickers}") from last_exc
    return pd.DataFrame()

def fetch_price_history_bulk(
    tickers: List[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    retries: int = 2,
    allow_empty: bool = False,
    cache: Optional[dict] = None,
    **fetch_kwargs: Any
) -> Dict[str, pd.Series]:
    """
    Fetch price history for multiple tickers and return dict[ticker] -> Series (Adj Close or Close).
    Uses safe_fetch to handle retries, backoff and kwargs like auto_adjust, threads.
    """
    cache_key = None
    if cache is not None:
        cache_key = f"bulk:{','.join(sorted(tickers))}:{start}:{end}:{interval}:{fetch_kwargs}"

    try:
        df = safe_fetch(
            tickers,
            start=start,
            end=end,
            interval=interval,
            retries=retries,
            cache=cache,
            cache_key=cache_key,
            **fetch_kwargs
        )
    except Exception as exc:
        logger.warning("fetch_price_history_bulk: safe_fetch failed for %s: %s", tickers, exc)
        if allow_empty:
            return {}
        raise

    if df is None or df.empty:
        logger.warning("fetch_price_history_bulk: fetched DataFrame is empty for %s", tickers)
        if allow_empty:
            return {}
        raise ValueError("fetch_price_history_bulk: fetched prices are empty")

    result: Dict[str, pd.Series] = {}
    for col in df.columns:
        col_data = df[col]
        if isinstance(col_data, pd.DataFrame):
            if "Adj Close" in col_data.columns:
                series = col_data["Adj Close"]
            elif "Close" in col_data.columns:
                series = col_data["Close"]
            else:
                numeric_cols = [c for c in col_data.columns if pd.api.types.is_numeric_dtype(col_data[c])]
                series = col_data[numeric_cols[0]] if numeric_cols else col_data.iloc[:, 0]
        else:
            series = col_data

        series = series.dropna().sort_index()
        result[col] = series

    return result


def fetch_price_history(symbol: str, period: str = "5y") -> Optional[pd.Series]:
    return fetch_price_history_bulk([symbol], start=None, end=None, interval="1d").get(symbol)

def price_history_to_prices_df(price_history: dict) -> pd.DataFrame:
    """
    price_history: dict[ticker] -> pd.Series (DatetimeIndex)
    returns DataFrame indexed by date, columns = tickers (sorted)
    """
    if not price_history:
        return pd.DataFrame()

    # concat outer join, keys = tickers
    df = pd.concat(price_history.values(), axis=1, keys=price_history.keys())
    # flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.sort_index().ffill().dropna(how="all")
    # keep only numeric columns (safety)
    df = df.select_dtypes(include="number")
    return df

def extract_close_series(df, ticker):
    """
    Extrahiert die Close-Serie eines einzelnen Tickers aus einem DataFrame.
    Robust gegen MultiIndex, verschiedene Spaltennamen und fehlende Daten.
    """

    if df is None or df.empty:
        return pd.Series(dtype=float)

    # MultiIndex flatten falls nötig
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if "Close" in df.columns.get_level_values(0):
                df = df.xs("Close", axis=1, level=0, drop_level=False)
            else:
                df.columns = df.columns.get_level_values(-1)
        except Exception:
            df.columns = df.columns.get_level_values(-1)

    # mögliche Spaltennamen
    candidates = [
        ticker,
        ticker.upper(),
        ticker.lower(),
        "Close",
        "close",
        "Adj Close",
        "adjclose"
    ]

    for col in candidates:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                return s

    # fallback: erste numerische Spalte
    numeric_cols = df.select_dtypes("number").columns.tolist()
    if numeric_cols:
        return df[numeric_cols[0]].dropna()

    return pd.Series(dtype=float)

def fetch_prices_quiet_with_used(tickers: Sequence[str] | str,
                                 start: str = DEFAULT_START_STR,
                                 end: Optional[str] = None,
                                 auto_adjust: bool = False,
                                 threads: bool = True,
                                 progress: bool = False) -> Tuple[Optional[str], pd.DataFrame]:
    """
    Lade Close/Adj Close Preise für tickers via yfinance.
    Rückgabe: (used_ticker_or_column_name, dataframe)
    - used: erster Ticker (aus input order), der tatsächlich Daten liefert; oder None.
    - dataframe: DatetimeIndex, Spalten = TICKER (uppercased)
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return None, pd.DataFrame()

    logger.debug("fetch_prices_quiet_with_used start tickers=%s start=%s end=%s", tickers, start, end)

    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            progress=progress,
            group_by="ticker",
            auto_adjust=auto_adjust,
            threads=threads
        )
    except Exception as e:
        logger.warning("yfinance download failed for %s: %s", tickers, e)
        return None, pd.DataFrame()

    if raw is None or raw.empty:
        logger.warning("fetch_prices_quiet_with_used returned empty for %s", tickers)
        return None, pd.DataFrame()

    # Robustes Flattening
    df = flatten_yf_dataframe(raw)

    # Spalten auf Großbuchstaben (einheitlich)
    df.columns = [str(c).upper() for c in df.columns]

    # Bestimme 'used' als erster Ticker, der tatsächlich Spalte liefert
    used = None
    for t in tickers:
        if str(t).upper() in df.columns:
            used = str(t).upper()
            break
    if used is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        used = numeric_cols[0] if numeric_cols else None

    # Index in Datetime konvertieren
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    df = df.sort_index()
    logger.debug("fetch_prices_quiet_with_used returning used=%s df.shape=%s", used, df.shape)
    return used, df
