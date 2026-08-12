import yfinance as yf
import pandas as pd

from typing import List
import logging


from risk_dashboard.data_utils import flatten_yf_dataframe, fetch_prices_from_yf

logger = logging.getLogger(__name__)


def download_fx_history(tickers, period="10y") -> pd.DataFrame:
    """
    Lade FX History für tickers über zentrale fetch_prices_from_yf.
    Liefert DataFrame mit DatetimeIndex und Spalten pro Ticker.
    """
    try:
        df = fetch_prices_from_yf(tickers, start=None, end=None, interval="1d")
    except Exception as e:
        logger.exception("fetch_prices_from_yf failed: %s", e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    # Falls MultiIndex, flatten defensiv
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = flatten_yf_dataframe(df)
        except Exception:
            pass

    # Bevorzuge ADJ CLOSE -> CLOSE -> erste numerische Spalte
    df_cols = [c.upper() for c in df.columns]
    if "ADJ CLOSE" in df_cols or "ADJ_CLOSE" in df_cols:
        col = next(c for c in df.columns if c.upper().replace("_"," ") == "ADJ CLOSE" or c.upper() == "ADJ_CLOSE")
        out = df[[col]].copy()
    elif "CLOSE" in df_cols:
        col = next(c for c in df.columns if c.upper() == "CLOSE")
        out = df[[col]].copy()
    else:
        numeric = df.select_dtypes(include="number")
        if numeric.shape[1] > 0:
            out = numeric.iloc[:, :].copy()
        else:
            raise KeyError("Neither 'Adj Close' nor 'Close' found in downloaded FX data")

    # Falls Series -> DataFrame handled above; ensure DataFrame
    if isinstance(out, pd.Series):
        out = out.to_frame()

    # Säubere Spaltennamen
    out.columns = [str(c).strip() for c in out.columns]
    return out