# risk_dashboard/data_utils.py
import pandas as pd
import yfinance as yf
import logging
from typing import List, Optional

# Logging in Datei
logger = logging.getLogger("risk_dashboard.data_utils")


def _is_multiindex_df(df: pd.DataFrame) -> bool:
    return getattr(df.columns, "nlevels", 1) > 1

def _safe_adj_from_multi(df: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
    """Versuche verschiedene Feldnamen in MultiIndex zu finden."""
    try:
        return df[ticker]['Adj Close']
    except Exception:
        for alt in ['Adj_Close', 'AdjClose', 'Close']:
            try:
                return df[ticker][alt]
            except Exception:
                continue
    return None

def fetch_prices_quiet(tickers: List[str], start: str = None, end: str = None, batch_size: int = 50) -> pd.DataFrame:
    """
    Lade Adjusted Close Preise für tickers. Liefert DataFrame mit Spalten = tickers.
    Wir behandeln SingleTicker Series, SingleIndex DataFrames und MultiIndex DataFrames.
    """
    logger.debug("fetch_prices_quiet start tickers=%s start=%s end=%s", tickers, start, end)
    if not tickers:
        return pd.DataFrame()

    # Entferne offensichtliche OHLC/Meta Strings
    forbidden = {"OPEN", "HIGH", "LOW", "CLOSE", "ADJ CLOSE", "ADJ_CLOSE", "VOLUME"}
    tickers = [t for t in tickers if str(t).upper() not in forbidden]
    if not tickers:
        logger.warning("Kein gültiger Ticker nach OHLC/VOLUME-Filter.")
        return pd.DataFrame()

    # Batch download
    parts = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            df = yf.download(batch, start=start, end=end, group_by='ticker', threads=True, progress=False)
            if df is None or df.empty:
                logger.warning("yfinance returned empty for batch %s", batch)
                continue
            parts.append(df)
            logger.debug("Batch download successful for %s", batch)
        except Exception as e:
            logger.exception("Batch download failed for %s: %s", batch, e)

    if not parts:
        logger.error("Keine Daten von yfinance erhalten für alle Batches")
        return pd.DataFrame()

    df = pd.concat(parts, axis=1)

    # Fall 1 MultiIndex (ticker, field)
    if _is_multiindex_df(df):
        logger.debug("DataFrame is MultiIndex with levels %s", df.columns.nlevels)
        adj = {}
        invalid = []
        for t in tickers:
            if t in df.columns.get_level_values(0):
                series = _safe_adj_from_multi(df, t)
                if series is not None:
                    adj[t] = series
                else:
                    invalid.append(t)
            else:
                invalid.append(t)
        if invalid:
            logger.info("Ungültige Ticker (kein Adj gefunden) %s", invalid)
        if not adj:
            logger.error("Keine gültigen Ticker in prices_df nach MultiIndex Verarbeitung")
            raise ValueError("Keine gültigen Ticker in prices_df")
        adj_df = pd.DataFrame(adj)

    else:
        # Fall 2 SingleIndex oder Series
        logger.debug("DataFrame is SingleIndex or Series. Columns: %s", list(df.columns[:20]))
        # Wenn nur eine Spalte 'Adj Close' vorhanden (single ticker download)
        if 'Adj Close' in df.columns and df.shape[1] == 1:
            # rename to ticker name falls möglich
            single_name = tickers[0] if len(tickers) == 1 else tickers[0]
            adj_df = df[['Adj Close']].rename(columns={'Adj Close': single_name})
            logger.debug("Single ticker with 'Adj Close' column, renamed to %s", single_name)
        else:
            # Versuche, Spalten zu matchen
            adj = {}
            invalid = []
            for t in tickers:
                if t in df.columns:
                    adj[t] = df[t]
                else:
                    # Versuche alternative Spaltennamen
                    found = False
                    for alt in (f"{t} Adj Close", f"{t}AdjClose", f"{t} Close"):
                        if alt in df.columns:
                            adj[t] = df[alt]
                            found = True
                            break
                    if not found:
                        invalid.append(t)
            if invalid:
                logger.info("Ungültige Ticker (SingleIndex, keine Spalte gefunden): %s", invalid)
            if not adj:
                logger.error("Keine gültigen Ticker in prices_df nach SingleIndex Verarbeitung")
                raise ValueError("Keine gültigen Ticker in prices_df")
            adj_df = pd.DataFrame(adj)

    # Pandas 3 kompatibel: forward/backfill und leere Spalten entfernen
    adj_df = adj_df.ffill().bfill().dropna(axis=1, how='all')

    # Sortiere Spalten in ursprünglicher Reihenfolge
    cols = [c for c in tickers if c in adj_df.columns]
    adj_df = adj_df[cols]

    logger.debug("fetch_prices_quiet returning dataframe with columns %s and index %s", list(adj_df.columns), adj_df.index[:3])
    return adj_df

