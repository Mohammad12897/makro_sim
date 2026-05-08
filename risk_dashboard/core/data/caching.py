# core/data/caching.py
import functools
import yfinance as yf
from .logging import logger

@functools.lru_cache(maxsize=256)
def cached_download(symbol: str, period: str = "5y", auto_adjust: bool = True):
    logger.info(f"Downloading data for {symbol}, period={period}")
    data = yf.download(symbol, period=period, progress=False, auto_adjust=auto_adjust)
    return data
