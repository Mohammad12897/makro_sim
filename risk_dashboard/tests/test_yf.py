import yfinance as yf
import requests
import pandas as pd
import logging

logger = logging.getLogger(__name__)

#ticker = "EUNL.DE"
ticker = "CSPX.L"

logger.debug("== Python / pandas / yfinance Versions ==")
import sys
logger.debug("python", sys.version.split()[0])
logger.debug("pandas", pd.__version__)
import yfinance
logger.debug("yfinance", yfinance.__version__)

logger.debug("\n== Direct HTTP check to Yahoo download endpoint ==")
url = "https://query1.finance.yahoo.com/v7/finance/download/EUNL.DE?period1=1451606400&period2=1704067200&interval=1d&events=history&includeAdjustedClose=true"
try:
    r = requests.get(url, timeout=10)
    logger.debug("HTTP status:", r.status_code)
    logger.debug("Content starts:", r.text[:200].replace("\n", "\\n"))
except Exception as e:
    logger.debug("HTTP error:", repr(e))

logger.debug("\n== yf.download (period=10y) ==")
try:
    df = yf.download(ticker, period="10y", auto_adjust=True, progress=False)
    logger.debug("download shape:", None if df is None else df.shape)
    if df is not None and not df.empty:
        logger.debug("First index:", df.index.min(), "Last index:", df.index.max())
    else:
        logger.debug("download returned empty")
except Exception as e:
    logger.debug("download error:", repr(e))

logger.debug("\n== yf.Ticker.history (period=10y) ==")
try:
    t = yf.Ticker(ticker)
    df2 = t.history(period="10y", auto_adjust=True)
    logger.debug("history shape:", None if df2 is None else df2.shape)
    if df2 is not None and not df2.empty:
        logger.debug("First index:", df2.index.min(), "Last index:", df2.index.max())
    else:
        logger.debug("history returned empty")
except Exception as e:
    logger.debug("history error:", repr(e))


