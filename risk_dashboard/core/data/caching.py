# core/data/caching.py
import functools
from typing import Optional
import pandas as pd
import logging

from risk_dashboard.data_utils import safe_fetch

logger = logging.getLogger(__name__)

@functools.lru_cache(maxsize=256)
def cached_fetch_prices(symbol: str, period: str = "5y", auto_adjust: bool = True) -> Optional[pd.DataFrame]:
    """
    Cache wrapper für safe_fetch. Achtung: lru_cache serialisiert nur Hashable args.
    Verwende symbol als String (kein List).
    """
    logger.info("Downloading data for %s, period=%s", symbol, period)
    # safe_fetch erwartet ticker oder Liste; wir übergeben String
    df = safe_fetch(symbol, start=None, end=None, interval="1d", auto_adjust=auto_adjust)
    return df