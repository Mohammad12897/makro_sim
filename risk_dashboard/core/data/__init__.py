#core/data/ticker_validation.py
import yfinance as yf

# Manuelle Korrekturen fÃ¼r bekannte ProblemfÃ¤lle
TICKER_CORRECTIONS = {
    "IEGA.DE": "EUNA.DE",   # iShares Euro Gov Bond â†’ neuer Ticker
    "AGGH.DE": "AGGH.L",    # Beispiel
}

# Fallback-Liste, falls ein ETF delisted ist
TICKER_FALLBACKS = {
    "IEGA.DE": "EUNA.DE",
    "EUNA.DE": "AGGH.DE",
}

def is_valid_ticker(ticker: str) -> bool:
    try:
        test = yf.Ticker(ticker).history(period="1mo")
        return not test.empty
    except:
        return False

def correct_ticker(ticker: str) -> str:
    # 1. Manuelle Korrektur
    if ticker in TICKER_CORRECTIONS:
        return TICKER_CORRECTIONS[ticker]

    # 2. Wenn gÃ¼ltig â†’ OK
    if is_valid_ticker(ticker):
        return ticker

    # 3. Fallback prÃ¼fen
    if ticker in TICKER_FALLBACKS:
        fb = TICKER_FALLBACKS[ticker]
        if is_valid_ticker(fb):
            return fb

    # 4. Wenn alles fehlschlÃ¤gt â†’ None
    return None

def validate_or_fix_ticker(ticker: str):
    fixed = correct_ticker(ticker)
    return fixed


