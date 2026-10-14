# risk_dashboard/price_utils.py
import pandas as pd

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
