# core/backend/symbol_tools.py
import re
import yfinance as yf
from core.data.logging import logger
import requests
from core.backend.isin_database import ISIN_DATABASE
from core.backend.isin_database import load_isin_db, save_isin_db
from core.data.db_assets import ETF_DB, STOCK_DB, find_asset
import pandas as pd

COMMON_SYMBOLS = [
    "SPY", "VTI", "QQQ", "GLD", "IAU", "BTC-USD", "ETH-USD",
    "EUNL.DE", "EUNA.DE", "VUKE.L", "CSUK.L", "AAPL", "MSFT",
    "AMZN", "GOOGL", "META", "TSLA", "NVDA", "NFLX", "QQQM", "GC=F"
]

ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

def is_isin(text: str) -> bool:
    return bool(ISIN_PATTERN.match(text.strip().upper()))

def validate_symbol(symbol: str) -> bool:
    symbol = symbol.strip()
    try:
        data = yf.Ticker(symbol).history(period="1mo")
        if data is None or data.empty:
            logger.warning(f"Symbol validation failed: {symbol}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}")
        return False

def suggest_symbols(prefix: str, limit: int = 10):
    prefix = prefix.strip().upper()
    if not prefix:
        return COMMON_SYMBOLS[:limit]
    candidates = [s for s in COMMON_SYMBOLS if s.startswith(prefix)]
    return candidates[:limit]

def detect_symbol_type(text: str) -> str:
    t = text.strip().upper()
    if is_isin(t):
        return "isin"
    if t.endswith("-USD"):
        return "krypto"
    if "=" in t:
        return "future"
    if "." in t:
        return "etf/aktie"
    return "ticker"



def yahoo_search_isin(ticker: str) -> str | None:
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}"
        data = requests.get(url, timeout=5).json()
        if "quotes" in data:
            for q in data["quotes"]:
                if q.get("symbol", "").upper() == ticker.upper():
                    return q.get("isin")
    except Exception:
        pass
    return None


def ticker_to_isin(ticker: str) -> str | None:
    db = load_isin_db()
    t = ticker.strip().upper()

    # 1. Lokale DB
    if t in db:
        return db[t]

    # 2. Yahoo versuchen
    isin = yahoo_search_isin(t)
    if isin:
        db[t] = isin
        save_isin_db(db)
        return isin

    # 3. Keine ISIN (z. B. Krypto)
    db[t] = None
    save_isin_db(db)
    return None
