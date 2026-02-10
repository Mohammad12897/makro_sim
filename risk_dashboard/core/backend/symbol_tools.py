# core/backend/symbol_tools.py
import re
import yfinance as yf
from core.data.logging import logger
import requests

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

  

def ticker_to_isin(ticker: str) -> str | None:
    """
    Holt die ISIN eines Tickers über die OpenFIGI API.
    Funktioniert für Aktien & ETFs.
    Gibt None zurück, wenn keine ISIN existiert (z. B. bei Krypto).
    """

    url = "https://api.openfigi.com/v3/mapping"
    headers = {"Content-Type": "application/json"}

    payload = [{
        "idType": "TICKER",
        "idValue": ticker,
        "exchCode": None
    }]

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        data = r.json()

        if isinstance(data, list) and len(data) > 0:
            result = data[0].get("data")
            if result and len(result) > 0:
                return result[0].get("isin")
    except Exception:
        pass

    return None


def convert_tickers_to_isins(tickers: list[str]) -> list[tuple[str, str | None]]:
    """
    Konvertiert eine Liste von Ticker-Symbolen in ISINs.
    Gibt eine Liste von (ticker, isin) zurück.
    """
    result = []
    for t in tickers:
        t_clean = t.strip().upper()
        isin = ticker_to_isin(t_clean)
        result.append((t_clean, isin))
    return result
