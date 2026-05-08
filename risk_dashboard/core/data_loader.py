# risk_dashboard/core/data_loader.py
import pandas as pd
from typing import List, Dict, Tuple
from yfinance import download
import logging

logger = logging.getLogger(__name__)
SUFFIXES = ["", ".DE", ".L", ".US", ".AX"]

def try_download_with_alternatives(ticker_base: str, start: str = None, end: str = None) -> Tuple[str, pd.Series]:
    for s in SUFFIXES:
        t = ticker_base + s
        try:
            df = download(t, start=start, end=end, progress=False)
            if df is not None and not df.empty:
                col = "Adj Close" if "Adj Close" in df.columns else df.columns[-1]
                srs = df[col].rename(t)
                srs.index = pd.to_datetime(srs.index)
                logger.info("Download success for %s -> %s", ticker_base, t)
                return t, srs
        except Exception as e:
            logger.debug("Download failed for %s (tried %s): %s", ticker_base, t, e)
            continue
    logger.warning("No data for ticker base %s with any suffixes", ticker_base)
    return None, pd.Series(dtype=float)

def fetch_prices(tickers: List[str], start: str = "2018-01-01", end: str = None) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {}
    for tbase in tickers:
        # 1) try exact ticker first
        try:
            df = download(tbase, start=start, end=end, progress=False)
            if df is not None and not df.empty:
                col = "Adj Close" if "Adj Close" in df.columns else df.columns[-1]
                srs = df[col].rename(tbase)
                srs.index = pd.to_datetime(srs.index)
                out[tbase] = srs
                continue
        except Exception:
            pass

        # 2) try alternatives
        success_ticker, series = try_download_with_alternatives(tbase, start=start, end=end)
        if success_ticker is not None and not series.empty:
            out[success_ticker] = series
        else:
            out[tbase] = pd.Series(dtype=float)  # placeholder for missing
    return out
