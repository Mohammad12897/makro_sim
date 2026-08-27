# risk_dashboard/core/etl.py
import pandas as pd
from typing import Tuple, Dict, List
from datetime import datetime
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.data_loader import load_raw_prices_for_universe
from risk_dashboard.config import DEFAULT_START_STR
from risk_dashboard.data_utils import flatten_yf_dataframe
import logging

logger = logging.getLogger(__name__)


# --- Robust: bring prices_multi into long format with columns Date, __ticker, Close ---
def ensure_long_prices(prices_multi: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize various fetch outputs into a long DataFrame with columns:
    Date, __ticker, Close
    """

    # --- 1) MultiIndex columns flatten ---
    if isinstance(prices_multi.columns, pd.MultiIndex):
        prices_multi.columns = ['_'.join(map(str, c)).strip() for c in prices_multi.columns.values]

    # --- 2) Ensure Date column exists ---
    if "Date" not in prices_multi.columns:
        prices_multi = prices_multi.reset_index().rename(columns={prices_multi.index.name or "index": "Date"})

    # --- 3) Detect LONG format ---
    if "__ticker" in prices_multi.columns and "Close" in prices_multi.columns:
        # Already long format
        prices_multi["Date"] = pd.to_datetime(prices_multi["Date"], errors="coerce")
        return prices_multi[["Date", "__ticker", "Close"]].dropna()

    # --- 4) WIDE → LONG ---
    # All columns except Date are tickers
    ticker_cols = [c for c in prices_multi.columns if c != "Date"]

    prices_multi = prices_multi.melt(
        id_vars="Date",
        value_vars=ticker_cols,
        var_name="__ticker",
        value_name="Close"
    )

    # --- 5) Cleanup ---
    prices_multi["Date"] = pd.to_datetime(prices_multi["Date"], errors="coerce")
    prices_multi = prices_multi.dropna(subset=["Date", "__ticker", "Close"])
    prices_multi = prices_multi.sort_values(["__ticker", "Date"])

    # --- 6) Remove duplicates deterministically ---
    if prices_multi.duplicated(subset=["Date", "__ticker"]).any():
        prices_multi = prices_multi.groupby(["Date", "__ticker"], as_index=False)["Close"].last()

    return prices_multi

def build_ticker_list(etf_universes: Dict) -> List[str]:
    return [v["ticker"] for v in etf_universes.values() if v.get("ticker")]

def load_etf_universe_prices(start: str = DEFAULT_START_STR, end: str = None) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """
    Lädt historische Preise für alle Ticker in ETF_UNIVERSES.
    Rückgabe:
      - prices_df: DataFrame mit Datum als Index und Spalten = config-keys
      - missing_total: Liste der config-keys, die keine Daten lieferten
      - mapping: success_ticker -> config_key
    """
    start = start or DEFAULT_START_STR
    end = end or datetime.today().strftime("%Y-%m-%d")


    # 1) Universe bauen
    tickers = build_ticker_list(ETF_UNIVERSES)
    if not tickers:
        return pd.DataFrame(), [], {}

    # 2) NEU: robustes Laden aller Ticker
    prices_multi, skipped = load_raw_prices_for_universe(tickers)

    # falls leer: frühzeitig zurückgeben
    if prices_multi is None or getattr(prices_multi, "empty", False):
        return pd.DataFrame(), list(ETF_UNIVERSES.keys()), {}

    # 3) success_ticker -> config_key Mapping
    prices_multi = ensure_long_prices(prices_multi)
    logger.debug("AFTER ensure_long_prices: columns=%s head=\n%s",
             list(prices_multi.columns),
             prices_multi.head())
    success_to_key: Dict[str, str] = {}

    loaded_tickers = set(prices_multi['__ticker'].unique())
    for cfg_key, meta in ETF_UNIVERSES.items():
        base = meta.get("ticker")
        if not base:
            continue
        for loaded in loaded_tickers:
            if loaded == base or loaded.startswith(base):
                success_to_key[loaded] = cfg_key
                break

    # 4) DataFrame pivoten: MultiIndex → Wide Format
    # ensure we have a long DataFrame with columns Date, __ticker, Close
    if "Close" not in prices_multi.columns:
        # case 1: wide DataFrame with Date index and ticker columns
        if not isinstance(prices_multi.columns, pd.MultiIndex):
            wide = prices_multi.reset_index().rename(columns={'index':'Date'})
            ticker_cols = [c for c in wide.columns if c != "Date"]
            prices_multi = wide.melt(id_vars="Date", value_vars=ticker_cols, var_name="__ticker", value_name="Close")
        else:
            # case 2: MultiIndex from yfinance, flatten first
            prices_multi = flatten_yf_dataframe(prices_multi)  # implementiert in deinem Projekt
            if "Close" not in prices_multi.columns:
                wide = prices_multi.reset_index().rename(columns={'index':'Date'})
                ticker_cols = [c for c in wide.columns if c != "Date"]
                prices_multi = wide.melt(id_vars="Date", value_vars=ticker_cols, var_name="__ticker", value_name="Close")

    # ensure Date is datetime
    prices_multi['Date'] = pd.to_datetime(prices_multi['Date'], errors='coerce')

    # drop rows with missing Date or Close
    prices_multi = prices_multi.dropna(subset=['Date', 'Close'])

    # sort for deterministic grouping
    prices_multi = prices_multi.sort_values(['__ticker', 'Date'])

    # if duplicates for same (Date, __ticker) exist, aggregate deterministically (last, mean, or first)
    if prices_multi.duplicated(subset=['Date', '__ticker']).any():
        # choose aggregation strategy: 'last' is safe if later fetch overwrote earlier
        prices_multi = (
            prices_multi
            .groupby(['Date', '__ticker'], as_index=False)['Close']
            .last()
        )

    logger.debug("load_price_data: normalized tickers=%s", tickers)
    logger.debug("load_etf_universe_prices: prices_multi.columns=%s shape=%s", list(prices_multi.columns)[:20], prices_multi.shape)

    logger.debug("prices_multi.head():\n%s", prices_multi.head(20))
    logger.debug("prices_multi.duplicated count: %d", prices_multi.duplicated(subset=['Date','__ticker']).sum())
    logger.debug("unique tickers: %s", prices_multi['__ticker'].unique())

    # now pivot safely using pivot_table with aggfunc as extra safety
    prices_df = prices_multi.pivot_table(index='Date', columns='__ticker', values='Close', aggfunc='first')


    # 5) Spalten umbenennen (success_ticker → config_key)
    prices_df = prices_df.rename(columns=success_to_key)

    # 6) Fehlende config_keys bestimmen
    missing_total = []
    for cfg_key in ETF_UNIVERSES.keys():
        if cfg_key not in prices_df.columns or prices_df[cfg_key].dropna().empty:
            missing_total.append(cfg_key)

    return prices_df, missing_total, success_to_key