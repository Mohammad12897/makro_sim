# risk_dashboard/data_utils.py
from typing import Optional, Sequence, Tuple, List
import pandas as pd
import yfinance as yf
import logging


logger = logging.getLogger(__name__)


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

def fetch_prices_from_yf(tickers, start="2010-01-01", end=None,
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
                                 start: str = "2010-01-01",
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