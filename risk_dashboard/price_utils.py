# risk_dashboard/price_utils.py
import re

import pandas as pd
import logging


logger = logging.getLogger(__name__)

def _pick_price_column(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    # prefer adj close, then close (case-insensitive)
    for cand in ("adj close", "adj_close", "adjclose", "close"):
        for c in cols:
            if c.lower() == cand:
                return c
    # fallback: first numeric column
    numeric = df.select_dtypes(include="number").columns
    if len(numeric) > 0:
        return numeric[0]
    # last resort: first column name
    return cols[0]

def _extract_price_series_from_yf(raw_df: pd.DataFrame, prefer="Adj Close"):
    """
    raw_df: DataFrame returned by yf.download (may be MultiIndex or single-level)
    returns: DataFrame with single-level columns = normalized tickers (e.g. 'NVDA', 'BTC-USD')
    """
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    # MultiIndex case
    if isinstance(raw_df.columns, pd.MultiIndex):
        if prefer in raw_df.columns.levels[0]:
            df = raw_df[prefer].copy()
        else:
            # fallback to 'Close' or first level
            if 'Close' in raw_df.columns.levels[0]:
                df = raw_df['Close'].copy()
            else:
                # try to pick numeric columns per ticker
                df = raw_df.xs(raw_df.columns.levels[0][0], axis=1, level=0).copy()
    else:
        # single-level: try common names (case-insensitive)
        cols = [c for c in raw_df.columns if str(c).lower() in ('adj close','close','close*','close')]
        if cols:
            df = raw_df[cols].copy()
        else:
            # fallback: take all numeric columns
            numeric = raw_df.select_dtypes(include='number')
            if not numeric.empty:
                df = numeric.copy()
            else:
                df = raw_df.copy()

    # normalize column names (strip, upper, keep ticker-like)
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def to_wide_prices(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Versucht, ein Long-Format (Date, __ticker/ticker, Close) in Wide (Ticker-Spalten) zu konvertieren.
    Wenn input bereits Wide ist, wird es unverändert zurückgegeben.
    Defensive: erkennt typische OHLC-Spalten und pivotiert nur, wenn sinnvoll.
    """
    if prices_df is None or prices_df.empty:
        return pd.DataFrame()

    cols_lower = [c.lower() for c in prices_df.columns]

    # Heuristik: wenn DataFrame nur OHLC-ähnliche Spalten hat, ist es wahrscheinlich Wide mit MultiIndex
    ohlc_set = {"open", "high", "low", "close", "adj close", "volume"}
    if set(cols_lower) == ohlc_set:
        # Das ist kein Wide mit Ticker-Spalten, sondern ein OHLC-Block (unpivoted?) -> nichts tun
        return prices_df

    # Wenn bereits viele Spalten aussehen wie TICKER (z.B. 'AAPL', 'BTC-USD', 'EXS1.DE'), gib zurück
    if any(re.match(r'^[A-Z0-9\.\-]{1,10}$', str(c)) for c in prices_df.columns):
        return prices_df

    # Suche nach Long-Format-Spalten
    ticker_col = next((c for c in prices_df.columns if c.lower() in ("__ticker", "ticker", "symbol")), None)
    close_col = next((c for c in prices_df.columns if c.lower() in ("close", "adj close", "adj_close", "price")), None)
    date_col = next((c for c in prices_df.columns if c.lower() in ("date", "index", "timestamp")), None)

    if ticker_col and close_col:
        # setze Datum falls vorhanden
        if date_col:
            prices_df[date_col] = pd.to_datetime(prices_df[date_col], errors="coerce")
            prices_df = prices_df.dropna(subset=[date_col])
            idx = date_col
        else:
            idx = None

        try:
            pivoted = prices_df[[ticker_col, close_col]].reset_index().pivot_table(
                index=idx,
                columns=ticker_col,
                values=close_col,
                aggfunc='last'
            )
            pivoted = pivoted.sort_index().ffill()
            pivoted.columns = [str(c).strip().upper() for c in pivoted.columns]
            return pivoted
        except Exception:
            logger.exception("Pivot to wide failed in to_wide_prices")
            return pd.DataFrame()

    # Keine Umwandlung möglich
    return pd.DataFrame()


def build_last_price_map(prices_df: pd.DataFrame, tickers: list, normalize_fn) -> dict:
    last_prices = {}
    if prices_df is None or prices_df.empty:
        return last_prices

    # Wide format: ticker columns
    cols_norm = {normalize_fn(str(c)): c for c in prices_df.columns}
    for t in tickers:
        tn = normalize_fn(t)
        if tn in cols_norm:
            col = cols_norm[tn]
            last_series = prices_df[col].ffill().dropna()
            if not last_series.empty:
                last_prices[tn] = float(last_series.iloc[-1])

    # Long format: look for ticker column + close column
    cols_lower = [c.lower() for c in prices_df.columns]
    ticker_col = next((c for c in prices_df.columns if c.lower() in ("__ticker","ticker","symbol")), None)
    close_col = next((c for c in prices_df.columns if c.lower() in ("close","adj close","adj_close","price")), None)

    if ticker_col and close_col:
        grp = prices_df[[ticker_col, close_col]].dropna(subset=[ticker_col])
        grp[ticker_col] = grp[ticker_col].astype(str).apply(normalize_fn)
        last_by_t = grp.groupby(ticker_col)[close_col].apply(lambda s: s.ffill().dropna().iloc[-1] if not s.ffill().dropna().empty else None)
        for t in tickers:
            tn = normalize_fn(t)
            if tn in last_by_t.index and pd.notna(last_by_t.loc[tn]):
                last_prices.setdefault(tn, float(last_by_t.loc[tn]))

    return last_prices
