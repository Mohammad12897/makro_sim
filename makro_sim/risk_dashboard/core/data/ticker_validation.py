#core/data/ticker_validation.py
import yfinance as yf

# Manuelle Korrekturen für bekannte Problemfälle
TICKER_CORRECTIONS = {
    "IEGA.DE": "EUNA.DE",   # iShares Euro Gov Bond → neuer Ticker
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

    # 2. Wenn gültig → OK
    if is_valid_ticker(ticker):
        return ticker

    # 3. Fallback prüfen
    if ticker in TICKER_FALLBACKS:
        fb = TICKER_FALLBACKS[ticker]
        if is_valid_ticker(fb):
            return fb

    # 4. Wenn alles fehlschlägt → None
    return None

def validate_or_fix_ticker(ticker: str):
    fixed = correct_ticker(ticker)
    return fixed
