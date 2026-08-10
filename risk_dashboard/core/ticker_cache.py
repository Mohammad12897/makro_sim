# scripts/ticker_cache.py
# python scripts/ticker_cache.py
import json
from pathlib import Path
import yfinance as yf
import logging
import time

CACHE_FILE = Path("cache/ticker_validity.json")
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

def validate_ticker_with_cache(ticker: str, ttl_days: int = 7) -> bool:
    """
    Prüft Ticker mit Cache.
    TTL = 7 Tage (konfigurierbar)
    """
    cache = load_cache()
    now = time.time()

    # Cache-Hit?
    if ticker in cache:
        entry = cache[ticker]
        age = now - entry["timestamp"]
        if age < ttl_days * 86400:
            return entry["valid"]

    # Cache-Miss → echte Prüfung
    valid = _validate_ticker_live(ticker)

    # Cache aktualisieren
    cache[ticker] = {
        "valid": valid,
        "timestamp": now
    }
    save_cache(cache)

    return valid

def _validate_ticker_live(ticker: str) -> bool:
    """
    Echte Yahoo-Prüfung (wird nur selten ausgeführt).
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return False

        hist = t.history(period="1mo", auto_adjust=True)
        if hist is None or hist.empty:
            return False

        return True

    except Exception:
        return False
