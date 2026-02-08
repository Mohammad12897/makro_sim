# core/backend/symbol_tools.py
import re
import yfinance as yf
from core.data.logging import logger

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
