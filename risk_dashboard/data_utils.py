# risk_dashboard/data_utils.py
import time, random, logging
from datetime import datetime, date, timedelta
from tracemalloc import start
from typing import List, Optional, Any, Dict, Sequence, Tuple
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from requests.exceptions import RequestException
from pathlib import Path
import inspect
from types import SimpleNamespace
from collections import deque
import re, json


from risk_dashboard.core.holdings import map_holdings_to_pricecols
from risk_dashboard.ticker_utils import normalize_ticker,_normalize_tickers, normalize_ticker_simple
from risk_dashboard.price_utils import to_wide_prices

logger = logging.getLogger(__name__)


MIN_DUMP_TOKEN_OCCURRENCES = 1
MAX_STR_LEN = 2000
TRUNCATE_STR_LEN = 500
TRUNCATE_LIST_LEN = 200



DEFAULT_MARKERS_FILE = Path(__file__).parents[1] / "docs" / "default_edge_markers.txt"
DOCS_EXAMPLE = Path(__file__).parents[1] / "docs" / "edge_tabs_example.txt"
from risk_dashboard.config import DEFAULT_START_STR

@st.cache_data(ttl=3600)
def cached_download_prices(tickers, start, end, **kwargs):
    from risk_dashboard.core.etf_tools import download_prices
    return download_prices(tickers, start=start, end=end, **kwargs)

def finalize_buckets(low, medium, high, prices_df: pd.DataFrame | None):
    """
    Normalize, dedupe and filter bucket lists against available price columns.
    Returns (low_final, med_final, high_final) as lists of normalized tickers.
    """
    def _prepare(bucket):
        seen = set()
        out = []
        for t in bucket or []:
            if not t:
                continue
            tn = normalize_ticker_simple(str(t)).upper()
            if tn in seen:
                continue
            seen.add(tn)
            out.append(tn)
        if isinstance(prices_df, pd.DataFrame) and not prices_df.empty:
            available = {c.upper() for c in prices_df.columns}
            out = [t for t in out if t in available]
        return out

    low_final = _prepare(low)
    med_final = _prepare(medium)
    high_final = _prepare(high)
    return low_final, med_final, high_final

def extract_ticker_from_col(colname: str) -> str:
    """
    Robustly extract a ticker token from a flattened yfinance column name.
    Heuristics (in order):
      1) prefer tokens that match ticker_pattern AND contain '.' or a digit or are ALL UPPERCASE (likely tickers)
      2) then prefer any token that matches ticker_pattern
      3) fallback: remove common words like adj/close/open and try again
      4) final fallback: return original string
    """
    s = str(colname)
    parts = re.split(r'[_\s]+', s)
    ticker_pattern = re.compile(r'^[A-Za-z0-9\.\-]{1,40}$')

    # 1) prefer tokens that look most like tickers (dot, digit, or all uppercase)
    candidates_strong = []
    for p in parts:
        if not p:
            continue
        if ticker_pattern.match(p):
            if ('.' in p) or any(ch.isdigit() for ch in p) or (p.isalpha() and p.upper() == p and len(p) > 1):
                candidates_strong.append(p)

    if candidates_strong:
        # prefer rightmost strong candidate (handles 'Adj Close_TICKER' and 'TICKER_Adj Close')
        return candidates_strong[-1]

    # 2) fallback: any token matching ticker pattern (rightmost)
    candidates_any = [p for p in parts if p and ticker_pattern.match(p)]
    if candidates_any:
        return candidates_any[-1]

    # 3) try removing common words and re-evaluate
    cleaned = re.sub(r'(?i)\b(adj|close|open|high|low|volume|adjclose|adj_close)\b', '', s)
    cleaned = cleaned.strip('_ ').strip()
    if ticker_pattern.match(cleaned):
        return cleaned

    # 4) final fallback: return original string
    return s

def _safe_serialize_value(v: Any):
    """Return a JSON-serializable representation for mixed payload values."""
    # Pandas objects
    if isinstance(v, pd.DataFrame):
        return {"__type": "dataframe", "columns": list(v.columns), "rows": v.to_dict(orient="records")}
    if isinstance(v, pd.Series):
        return {"__type": "series", "values": v.tolist(), "index": v.index.tolist()}
    # numpy types
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    # lists/tuples: ensure elements are serializable (flatten nested DataFrames)
    if isinstance(v, (list, tuple)):
        out = []
        for e in v:
            try:
                json.dumps(e)
                out.append(e)
            except Exception:
                out.append(repr(e))
        return out
    # dicts: sanitize recursively
    if isinstance(v, dict):
        return {k: _safe_serialize_value(val) for k, val in v.items()}
    # fallback: try json, else repr
    try:
        json.dumps(v)
        return v
    except Exception:
        return repr(v)

def normalize_envelope(resp: Any) -> dict:
    """Return a safe envelope dict with serializable payload/result."""
    if resp is None:
        return {"ok": False, "message": "no response", "result": {}, "payload": {}}
    if isinstance(resp, dict):
        envelope = {"ok": bool(resp.get("ok", True)), "message": resp.get("message"), "result": {}, "payload": {}}
        # normalize result
        raw_res = resp.get("result")
        if raw_res is None:
            envelope["result"] = {}
        elif isinstance(raw_res, (pd.DataFrame, pd.Series)):
            envelope["result"] = _safe_serialize_value(raw_res)
        elif isinstance(raw_res, dict):
            envelope["result"] = {k: _safe_serialize_value(v) for k, v in raw_res.items()}
        else:
            envelope["result"] = _safe_serialize_value(raw_res)
        # normalize payload
        raw_payload = resp.get("payload") or {}
        if isinstance(raw_payload, dict):
            envelope["payload"] = {k: _safe_serialize_value(v) for k, v in raw_payload.items()}
        else:
            envelope["payload"] = _safe_serialize_value(raw_payload)
        return envelope
    # if resp is a DataFrame or Series, wrap it
    if isinstance(resp, (pd.DataFrame, pd.Series)):
        return {"ok": True, "message": None, "result": _safe_serialize_value(resp), "payload": {}}
    # fallback
    return {"ok": True, "message": None, "result": repr(resp), "payload": {}}


def _sanitize_date_param(d):
    """
    Liefert None oder 'YYYY-MM-DD' (string). Akzeptiert None, pd.Timestamp, datetime, oder String.
    """
    if d is None:
        return None
    # pd.Timestamp oder datetime types
    #if isinstance(d, (pd.Timestamp, datetime.datetime, datetime.date)):
    if isinstance(d, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(d).date().isoformat()
    if isinstance(d, str):
        # bereits YYYY-MM-DD?
        if len(d) == 10 and d[4] == "-" and d[7] == "-":
            return d
        try:
            ts = pd.to_datetime(d, errors="coerce")
            if pd.isna(ts):
                return None
            return ts.date().isoformat()
        except Exception:
            return None
    return None

def safe_rerun(stop: bool = True):
    """
    Versucht st.experimental_rerun(); falls nicht vorhanden, setzt nur eine Flag.
    Wichtig: wir schreiben NICHT direkt app_sidebar_page_choice hier, weil das Widget
    bereits existieren könnte und Streamlit das nicht erlaubt.
    """
    rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        rerun_fn()
    else:
        st.session_state["_needs_rerun"] = True
        if stop:
            st.stop()
        # kein direktes Setzen von app_sidebar_page_choice hier
        
def run_analysis():
    logging.info("Analyse gestartet")
    # Beispiel: Dummy-Ergebnis
    return {"status": "ok", "tickers": st.session_state.get("user_tickers", [])}

def analyze_callback():
    if st.session_state.get("_analyzing"):
        return
    st.session_state["_analyzing"] = True
    try:
        # lange Analyse hier (oder delegiere an cached function)
        result = run_analysis()  # blockierend, aber in Callback
        st.session_state["analysis_result"] = result
    except Exception:
        logging.exception("analysis failed")
    finally:
        st.session_state["_analyzing"] = False
        safe_rerun(stop=True)

def do_add_tickers(holdings_list, prefix, asset_key, prices=None):
    """
    Reine Verarbeitungsfunktion.
    - Ändert st.session_state (Tickerlisten, mapping), ruft kein safe_rerun().
    - Gibt (mapped_cols, missing) zurück für UI-Feedback.
    """
    # normalize input
    holdings = [str(h).strip() for h in holdings_list if str(h).strip()]
    if not holdings:
        return [], []

    # mapping nur wenn prices vorhanden
    mapped_cols, missing = [], []
    if prices is not None:
        try:
            mapped_cols, missing = map_holdings_to_pricecols(holdings, prices.columns)
        except Exception:
            mapped_cols, missing = [], holdings[:]  # fallback: alles missing

    holding_to_price = {h: c for h, c in zip(holdings, mapped_cols)} if mapped_cols else {}

    # session list key
    list_key = f"{prefix}_user_tickers_{st.session_state.get(asset_key, 'ETF')}"
    lst = st.session_state.setdefault(list_key, [])
    existing_upper = {x.upper() for x in lst}
    for h in holdings:
        if h.upper() not in existing_upper:
            lst.append(h)
            existing_upper.add(h.upper())
    st.session_state[list_key] = lst

    # store mapping info
    st.session_state[f"{prefix}_holding_to_price"] = holding_to_price
    st.session_state[f"{prefix}_holding_missing"] = missing

    return mapped_cols, missing

def _load_edge_markers():
    # wie bei dir: lade aus docs, fallback auf DEFAULT_MARKERS_FILE
    try:
        text = DOCS_EXAMPLE.read_text(encoding="utf-8")
    except Exception:
        try:
            text = DEFAULT_MARKERS_FILE.read_text(encoding="utf-8")
        except Exception:
            return []
    markers = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # nur alphanumerische tokens, keine JSON-Blöcke
        token = re.sub(r'[^A-Za-z0-9_]', '', ln)
        if token:
            markers.append(token.lower())
    return markers

def sanitize_bt_etf(bt_etf):
    if not isinstance(bt_etf, dict):
        return bt_etf
    bt = dict(bt_etf)
    try:
        markers = _load_edge_markers()  # _load_edge_markers sollte in demselben Modul oder importiert sein
        markers = [re.sub(r'[^a-z0-9_]', '', m.lower()) for m in markers if m]
    except Exception:
        markers = []

    for k in list(bt.keys()):
        v = bt.get(k)
        if isinstance(v, str):
            s = v.lower()
            if markers and any(m in s for m in markers) and len(s) > MAX_STR_LEN:
                bt.pop(k, None)
                logging.warning("sanitize_bt_etf removed suspicious string key %s (len=%d)", k, len(s))
                continue
        if isinstance(v, (list, tuple)) and len(v) > TRUNCATE_LIST_LEN:
            bt[k] = list(v)[:TRUNCATE_LIST_LEN]
            logging.debug("sanitize_bt_etf truncated list key %s to %d items", k, TRUNCATE_LIST_LEN)

    ALLOWED_BT_KEYS = {"result", "payload", "prices", "portfolio_value", "trades", "ok", "message"}
    bt_clean = {k: v for k, v in bt.items() if k in ALLOWED_BT_KEYS}

    for k, v in list(bt_clean.items()):
        if isinstance(v, str) and len(v) > TRUNCATE_STR_LEN:
            bt_clean[k] = v[:TRUNCATE_STR_LEN] + "...[truncated]"
        if isinstance(v, (list, tuple, np.ndarray, pd.Series)) and len(v) > TRUNCATE_LIST_LEN:
            bt_clean[k] = list(v)[:TRUNCATE_LIST_LEN]

    return bt_clean

def sanitize_session_state():
    markers = _load_edge_markers()
    if not markers:
        return []
    removed = []
    for k in list(st.session_state.keys()):
        v = st.session_state.get(k)
        if not isinstance(v, str):
            continue
        s = v.lower()
        # heuristik: marker vorkommen UND sehr große Länge
        marker_hits = sum(1 for m in markers if m in s)
        if marker_hits >= MIN_DUMP_TOKEN_OCCURRENCES and len(s) > MAX_STR_LEN:
            # optional: erst in Backup verschieben, dann entfernen
            st.session_state.pop(k, None)
            removed.append(k)
            logging.warning("sanitize_session_state removed suspicious key %s len=%d hits=%d", k, len(s), marker_hits)
    if removed:
        logging.info("sanitize_session_state removed keys: %s", removed)
    return removed

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

def fetch_prices_from_yf(tickers, start=None, end=None, lookback_days: int = None,
                         interval: str = "1d", auto_adjust: bool = False,
                         threads: bool = False, **kwargs) -> pd.DataFrame:
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return pd.DataFrame()

    # compute start/end if lookback_days given
    if lookback_days is not None and start is None:
        end_date = end or datetime.utcnow().date().isoformat()
        end_ts = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(end_ts):
            end_ts = pd.Timestamp.utcnow()
        start_dt = (end_ts - pd.Timedelta(days=lookback_days)).date()
        start = start_dt.isoformat()
        end = end_ts.date().isoformat()

    start_s = _sanitize_date_param(start)
    end_s = _sanitize_date_param(end)

    logger.debug("yf.download tickers=%s start=%s end=%s interval=%s", tickers, start_s, end_s, interval)

    try:
        if start_s is None and end_s is None:
            raw = yf.download(
                tickers,
                period="5y",
                interval=interval,
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads,
                **kwargs
            )
        else:
            raw = yf.download(
                tickers,
                start=start_s,
                end=end_s,
                interval=interval,
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads,
                **kwargs
            )
    except ValueError as e:
        logger.error("yfinance ValueError for %s start=%s end=%s: %s", tickers, start_s, end_s, e)
        raw = None
    except Exception:
        logger.exception("Unexpected error calling yf.download for %s", tickers)
        raw = None

    if raw is None or (hasattr(raw, "empty") and raw.empty):
        logger.warning("fetch_prices_from_yf returned empty DataFrame for %s", tickers)
        return pd.DataFrame()

    # Log original columns (helps debug different yfinance outputs)
    try:
        logger.debug("fetch_prices_from_yf: raw.columns before flatten=%s", list(raw.columns))
    except Exception:
        pass

    # 1 Flatten MultiIndex columns ONCE
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = ['_'.join(map(str, c)).strip() for c in raw.columns]

    logger.debug("fetch_prices_from_yf: raw.columns after flatten=%s", list(raw.columns))

    # 2 Try pivot long->wide if needed (single call)
    try:
        cols_lower = [str(c).lower() for c in raw.columns]
        if "__ticker" in cols_lower or "ticker" in cols_lower or set(cols_lower) == {"open","high","low","close","adj close","volume"}:
            maybe_wide = to_wide_prices(raw)
            if not maybe_wide.empty:
                raw = maybe_wide
                logger.debug("fetch_prices_from_yf: converted raw to wide format with columns=%s", list(raw.columns))
    except Exception:
        logger.exception("fetch_prices_from_yf: pivot heuristic failed, continuing with raw")

    # 3 Extract price series robustly (Adj Close / Close / numeric)
    cols = list(raw.columns)
    adj_candidates = [c for c in cols if 'adj close' in str(c).lower() or 'adj_close' in str(c).lower()]
    if adj_candidates:
        adj = raw[adj_candidates].copy()
    else:
        close_candidates = [c for c in cols if 'close' in str(c).lower()]
        if close_candidates:
            adj = raw[close_candidates].copy()
        else:
            numeric_cols = raw.select_dtypes(include='number').columns
            if len(numeric_cols) > 0:
                adj = raw[numeric_cols].copy()
            else:
                logger.warning("fetch_prices_from_yf: no numeric price column found for %s", tickers)
                return pd.DataFrame()

    # Log before normalization
    logger.debug("fetch_prices_from_yf: adj.columns before normalize=%s", list(adj.columns))

    # 4 Normalize column names to ticker tokens using centralized extractor
    try:
        adj.columns = [normalize_ticker_simple(extract_ticker_from_col(c)) for c in adj.columns]
    except Exception:
        logger.exception("fetch_prices_from_yf: column normalization failed; returning adj as-is")

    # Log after normalization
    logger.debug("fetch_prices_from_yf: adj.columns after normalize=%s", list(adj.columns))

    # Duplicate check and diagnostic raw.columns if duplicates found
    if any(pd.Index(adj.columns).duplicated()):
        dup = pd.Index(adj.columns)[pd.Index(adj.columns).duplicated()].tolist()
        logger.warning("fetch_prices_from_yf: duplicate normalized columns %s", dup)
        logger.debug("fetch_prices_from_yf: raw.columns for duplicates=%s", list(raw.columns))

    # Index in Datetime and sort, forward fill
    try:
        adj.index = pd.to_datetime(adj.index, errors="coerce")
    except Exception:
        pass
    adj = adj.sort_index().ffill()

    logger.debug("fetch_prices_from_yf returning dataframe with columns %s and index length %d", list(adj.columns), len(adj.index))
    return adj

def fetch_last_prices(tickers, lookback_days: int = 365) -> dict:
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return {}

    price_df = fetch_prices_from_yf(tickers, lookback_days=lookback_days, interval="1d")
    if price_df is None or price_df.empty:
        return {}

    try:
        last_row = price_df.ffill().iloc[-1]
        # normalize keys
        return {t: float(last_row[col]) for col in price_df.columns
                for t in tickers
                if normalize_ticker_simple(str(col)) == normalize_ticker_simple(t) and pd.notna(last_row[col])}
    except Exception:
        return {}

def find_price_for_ticker(prices_df: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
    """
    Versucht, eine Price-Zeitreihe für 'ticker' in prices_df zu finden.
    Probiert Varianten (Ticker, Ticker.US, Ticker.DE, Ticker with .OQ->.US).
    Gibt die Series zurück oder None.
    """
    if prices_df is None or prices_df.empty:
        return None

    t = normalize_ticker(ticker)

    # direkte Übereinstimmung
    if t in prices_df.columns:
        return prices_df[t]

    # Varianten
    variants = [
        t,
        t + ".US",
        t + ".DE",
        t.replace(".OQ", ".US"),
    ]
    for v in variants:
        if v in prices_df.columns:
            return prices_df[v]

    # evtl. Spalten sind in MultiIndex (z.B. flatten_yf_dataframe anders strukturiert) —
    # versuche einfache contains-Match (vorsichtig)
    cols = list(prices_df.columns)
    for c in cols:
        if c.upper().startswith(t):
            return prices_df[c]

    return None

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
    raise_on_failure: bool = False,
    **fetch_kwargs: Any,
) -> pd.DataFrame:
    start = start or DEFAULT_START_STR
    end = end or datetime.today().strftime("%Y-%m-%d")

    if not tickers:
        logger.debug("safe_fetch: received empty tickers list")
        if allow_empty:
            return pd.DataFrame()
        raise ValueError("safe_fetch: tickers list is empty")

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
                {k: fetch_kwargs.get(k) for k in ("auto_adjust", "threads") if k in fetch_kwargs}
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

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
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

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
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

from multiprocessing import Process, Queue
import traceback


def _worker_download(q, tickers, start, end, auto_adjust, threads):
    start_s = _sanitize_date_param(start)
    end_s = _sanitize_date_param(end)
    logger.debug("yf.download tickers=%s start=%s end=%s", tickers, start_s, end_s)

    try:
        if start_s is None and end_s is None:
            raw = yf.download(
                tickers,
                period="5y",
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads
            )
        else:
            raw = yf.download(
                tickers,
                start=start_s,
                end=end_s,
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads
            )
        q.put(("ok", raw))
    except Exception:
        q.put(("err", traceback.format_exc()))

def safe_yf_download(tickers, start, end, auto_adjust=False, threads=False, timeout=60):
    q = Queue()
    p = Process(target=_worker_download, args=(q, tickers, start, end, auto_adjust, threads))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        logger.error("yf.download timed out and was terminated")
        return None, pd.DataFrame()
    if q.empty():
        logger.error("yf.download worker returned no result")
        return None, pd.DataFrame()
    status, payload = q.get()
    if status == "ok":
        return payload  # raw DataFrame
    else:
        logger.error("yf.download worker error: %s", payload)
        return None, pd.DataFrame()


def _normalize_yf_raw(raw, tickers):
    """
    Normalize yfinance raw download output to DataFrame with columns = uppercased tickers.
    Returns DataFrame or raises ValueError on unrecognized format.
    """
    if raw is None:
        return pd.DataFrame()

    # Series -> DataFrame (single ticker)
    if isinstance(raw, pd.Series):
        df = raw.to_frame()
        df.columns = [normalize_ticker_simple(tickers[0])]
        return df

    # flatten MultiIndex once (prevents tuple errors)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = ['_'.join(map(str, c)).strip() for c in raw.columns]

    # try pivot long->wide (to_wide_prices returns empty DF if not applicable)
    from risk_dashboard.price_utils import to_wide_prices
    try:
        maybe_wide = to_wide_prices(raw)
        if not maybe_wide.empty:
            raw = maybe_wide
    except Exception:
        logger.debug("_normalize_yf_raw: to_wide_prices pivot attempt failed, continuing")

    # If still MultiIndex (rare after flatten), try common patterns using level values
    if isinstance(raw.columns, pd.MultiIndex):
        cols = raw.columns
        lvl0 = cols.get_level_values(0)
        lvl1 = cols.get_level_values(1)
        field_candidates = ['close', 'adj close', 'adj_close', 'adjclose']

        # pattern: (ticker, field)
        if any(str(v).lower() in field_candidates for v in lvl1):
            for field in ['Close', 'Adj Close']:
                try:
                    df = raw.xs(field, axis=1, level=1, drop_level=True)
                    df.columns = [str(c).upper() for c in df.columns]
                    return df
                except Exception:
                    continue

        # pattern: (field, ticker)
        if any(str(v).lower() in field_candidates for v in lvl0):
            for field in ['Close', 'Adj Close']:
                try:
                    df = raw.xs(field, axis=1, level=0, drop_level=True)
                    df.columns = [str(c).upper() for c in df.columns]
                    return df
                except Exception:
                    continue

        # fallback: try to pick numeric column per ticker from flattened MultiIndex
        flattened = {}
        for t in tickers:
            t_up = t.upper()
            for col in raw.columns:
                # col may be tuple; compare stringified parts
                if t_up in str(col).upper():
                    s = raw[col]
                    if pd.api.types.is_numeric_dtype(s):
                        flattened[t_up] = s
                        break
        if flattened:
            return pd.concat(flattened, axis=1).sort_index()

        raise ValueError("Unable to normalize MultiIndex yfinance output")

    # Single-level DataFrame handling
    if isinstance(raw, pd.DataFrame):
        # single-column -> assume single ticker series
        if raw.shape[1] == 1:
            colname = raw.columns[0]
            df = raw.rename(columns={colname: tickers[0].upper()})
            return df

        # prefer columns that look like Adj Close / Close
        cols = list(raw.columns)
        adj_candidates = [c for c in cols if 'adj close' in str(c).lower() or 'adj_close' in str(c).lower()]
        if adj_candidates:
            df = raw[adj_candidates].copy()
            df.columns = [normalize_ticker_simple(c) for c in df.columns]
            return df

        close_candidates = [c for c in cols if 'close' in str(c).lower()]
        if close_candidates:
            df = raw[close_candidates].copy()
            df.columns = [normalize_ticker_simple(c) for c in df.columns]
            return df

        # fallback: keep numeric columns and uppercase names
        numeric_cols = [c for c in raw.columns if pd.api.types.is_numeric_dtype(raw[c])]
        if numeric_cols:
            df = raw[numeric_cols].copy()
            df.columns = [str(c).upper() for c in df.columns]
            return df

    raise ValueError("Unrecognized yfinance raw format")

def fetch_prices_sequential(tickers, start, end, auto_adjust=False) -> Tuple[Optional[str], pd.DataFrame]:
    """
    Robust fallback: fetch each ticker sequentially via Ticker.history.
    Returns (used_ticker_or_None, dataframe)
    """
    frames = []
    used = None
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            df = tk.history(start=start, end=end, auto_adjust=auto_adjust)
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.debug("fetch_prices_sequential: no data for %s", t)
                continue
            if 'Close' in df.columns:
                s = df['Close'].rename(t.upper())
            elif 'Adj Close' in df.columns:
                s = df['Adj Close'].rename(t.upper())
            else:
                numcols = df.select_dtypes(include=[np.number]).columns
                if len(numcols) == 0:
                    logger.debug("fetch_prices_sequential: no numeric columns for %s", t)
                    continue
                s = df[numcols[0]].rename(t.upper())
            frames.append(s)
            if used is None:
                used = t
        except Exception as e:
            logger.warning("fetch_prices_sequential: failed for %s: %s", t, e)
    if not frames:
        return None, pd.DataFrame()
    result = pd.concat(frames, axis=1).sort_index()
    return used, result

def fetch_prices_quiet_with_used(tickers: Sequence[str] | str,
                                 start: str = DEFAULT_START_STR,
                                 end: Optional[str] = None,
                                 auto_adjust: bool = False,
                                 threads: bool = False,
                                 progress: bool = False) -> Tuple[Optional[str], pd.DataFrame]:
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return None, pd.DataFrame()

    start_s = _sanitize_date_param(start)
    end_s = _sanitize_date_param(end)
    logger.debug("fetch_prices_quiet_with_used tickers=%s start=%s end=%s", tickers, start_s, end_s)

    try:
        if start_s is None and end_s is None:
            raw = yf.download(
                tickers,
                period="5y",
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads
            )
        else:
            raw = yf.download(
                tickers,
                start=start_s,
                end=end_s,
                progress=False,
                group_by="ticker",
                auto_adjust=auto_adjust,
                threads=threads
            )

        if raw is None or (hasattr(raw, "empty") and raw.empty):
            logger.warning("fetch_prices_quiet_with_used: empty result for %s", tickers)
            raise RuntimeError("yf.download returned empty")


        # flatten MultiIndex columns
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = ['_'.join(map(str, c)).strip() for c in raw.columns]

        # try pivot if long format detected
        from risk_dashboard.price_utils import to_wide_prices
        cols_lower = [str(c).lower() for c in raw.columns]
        if "__ticker" in cols_lower or "ticker" in cols_lower or set(cols_lower) == {"open","high","low","close","adj close","volume"}:
            maybe_wide = to_wide_prices(raw)
            if not maybe_wide.empty:
                raw = maybe_wide


        # --- Normalize format: try to convert long-format to wide if needed ---
        from risk_dashboard.price_utils import to_wide_prices
        try:
            cols_lower = [str(c).lower() for c in raw.columns]
            if "__ticker" in cols_lower or "ticker" in cols_lower or set(cols_lower) == {"open","high","low","close","adj close","volume"}:
                maybe_wide = to_wide_prices(raw)
                if not maybe_wide.empty:
                    raw = maybe_wide
                    logger.debug("fetch_prices_quiet_with_used: converted raw to wide format with columns=%s", list(raw.columns))
        except Exception:
            logger.exception("fetch_prices_quiet_with_used: pivot heuristic failed, continuing with raw")

        # --- Extract price series robustly (Adj Close / Close / numeric) ---
        cols = list(raw.columns)
        cols_lower = [str(c).lower() for c in cols]

        # prefer columns that contain 'adj close' or 'adj_close'
        adj_candidates = [c for c in cols if 'adj close' in str(c).lower() or 'adj_close' in str(c).lower()]
        if adj_candidates:
            adj = raw[adj_candidates].copy()
        else:
            close_candidates = [c for c in cols if 'close' in str(c).lower()]
            if close_candidates:
                adj = raw[close_candidates].copy()
            else:
                numeric_cols = raw.select_dtypes(include='number').columns
                if len(numeric_cols) > 0:
                    adj = raw[numeric_cols].to_frame().copy()
                else:
                    raise RuntimeError("No numeric price column found in yf.download result")

        # Normalisiere Spaltennamen (z. B. Ticker)
        # adj.columns = [normalize_ticker(c) for c in adj.columns]

        adj.columns = [
            normalize_ticker_simple(extract_ticker_from_col(c))
            for c in adj.columns
        ]

        # Index in Datetime und sortieren
        try:
            adj.index = pd.to_datetime(adj.index)
        except Exception:
            pass
        adj = adj.sort_index()

        used = next((t for t in tickers if normalize_ticker(t) in adj.columns), None)
        return used, adj

    except Exception as e:
        logger.warning("fetch_prices_quiet_with_used failed for %s: %s", tickers, e)
        used, df = fetch_prices_sequential(tickers, start, end, auto_adjust=auto_adjust)
        return used, df

def sanity_backtest(price_data: pd.DataFrame, weights: dict, min_rows: int = 60) -> Tuple[bool, str]:
    """
    Returns (ok, message). ok==True wenn Sanity checks passed.
    """
    if price_data is None or price_data.empty:
        return False, "Preisdaten fehlen oder sind leer."
    if not isinstance(weights, dict) or not weights:
        return False, "Gewichte fehlen oder sind ungültig."
    # check columns
    cols = [c.upper() for c in price_data.columns]
    missing = [t for t in weights.keys() if t.upper() not in cols]
    if missing:
        return False, f"Fehlende Preisspalten für: {missing}"
    # check index length
    if len(price_data) < min_rows:
        return False, f"Zu wenige Datenpunkte ({len(price_data)} < {min_rows})."
    # check weights numeric and sum
    vals = []
    for v in weights.values():
        try:
            vals.append(float(v))
        except Exception:
            return False, "Gewichte müssen numerisch sein."
    if any(np.isnan(vals)):
        return False, "Gewichte enthalten NaN."
    if sum(vals) <= 0:
        return False, "Summe der Gewichte muss > 0 sein."
    return True, "Sanity checks passed."

def is_prices_empty(prices: Any) -> bool:
    if prices is None:
        return True
    if hasattr(prices, "empty"):
        try:
            return bool(prices.empty)
        except Exception:
            return False
    if isinstance(prices, dict):
        return len(prices) == 0
    try:
        return len(prices) == 0
    except Exception:
        return False

def normalize_prices(prices: Any) -> pd.DataFrame:
    if prices is None:
        return pd.DataFrame()
    if isinstance(prices, pd.DataFrame):
        return prices
    if isinstance(prices, pd.Series):
        return prices.to_frame()
    if isinstance(prices, dict):
        try:
            # dict of ticker -> Series/DataFrame
            return pd.concat({k: v for k, v in prices.items()}, axis=1)
        except Exception:
            try:
                return pd.DataFrame(prices)
            except Exception:
                return pd.DataFrame()
    try:
        return pd.DataFrame(prices)
    except Exception:
        return pd.DataFrame()

def fetch_prices_for_ticker(ticker: str, start: str = None, end: str = None, interval: str = "1d", **kwargs) -> Optional[pd.DataFrame]:
    """
    Wrapper: versucht, Preisdaten für einen einzelnen Ticker zu laden.
    Gibt DataFrame/Series zurück oder None bei Fehler / no data.
    """
    start_s = _sanitize_date_param(start)
    end_s = _sanitize_date_param(end)

    try:
        # safe_fetch ist eure bestehende Funktion; passe den Namen an, falls anders
        df = safe_fetch([ticker], start=start_s, end=end_s, interval=interval, **kwargs)

        if df is None:
            logger.debug("fetch_prices_for_ticker: no data for %s (None)", ticker)
            return None

        # Falls safe_fetch ein dict zurückgibt, hole den Eintrag für ticker
        if isinstance(df, dict):
            val = df.get(ticker)
            if val is None:
                logger.debug("fetch_prices_for_ticker: dict returned but no key %s", ticker)
                return None
            df_norm = normalize_prices(val)
        else:
            df_norm = normalize_prices(df)

        if df_norm is None or df_norm.empty:
            logger.debug("fetch_prices_for_ticker: empty after normalize for %s", ticker)
            return None

        return df_norm

    except Exception:
        logger.exception("fetch_prices_for_ticker failed for %s", ticker)
        return None
