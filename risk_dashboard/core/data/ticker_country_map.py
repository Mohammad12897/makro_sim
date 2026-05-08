# core/data/ticker_country_map.py

import yfinance as yf

# --- Statisches Mapping (Fallback) ---
TICKER_COUNTRY = {
    "AAPL": "USA", "MSFT": "USA", "AMZN": "USA", "GOOGL": "USA",
    "META": "USA", "TSLA": "USA", "NVDA": "USA",
    "SAP.DE": "Deutschland", "DTE.DE": "Deutschland", "BMW.DE": "Deutschland",
    "VOW3.DE": "Deutschland", "EUNA.DE": "Deutschland", "4GLD.DE": "Deutschland",
    "CAC.PA": "Frankreich", "AIR.PA": "Frankreich", "MC.PA": "Frankreich",
    "VUKE.L": "UK", "ISF.L": "UK", "CSUK.L": "UK",
    "EWJ": "Japan", "XDJP.DE": "Japan",
    "SPY": "USA", "QQQ": "USA", "VT": "Global",
    "VEA": "Entwickelte Märkte", "VWO": "Schwellenländer",
}

# --- ETF Regionserkennung ---
ETF_REGIONS = {
    "SPY": "USA",
    "QQQ": "USA",
    "VT": "Global",
    "VEA": "Entwickelte Märkte",
    "VWO": "Schwellenländer",
    "EWJ": "Japan",
    "EEM": "Schwellenländer",
}

# --- ISO Mapping für ISIN ---
ISO_MAP = {
    "US": "USA",
    "DE": "Deutschland",
    "FR": "Frankreich",
    "GB": "UK",
    "JP": "Japan",
    "CH": "Schweiz",
    "CA": "Kanada",
    "AU": "Australien",
    "HK": "Hongkong",
    "CN": "China",
    "NL": "Niederlande",
    "ES": "Spanien",
    "IT": "Italien",
    "SE": "Schweden",
}


def auto_detect_country(ticker: str) -> str:
    """
    Automatische Ländererkennung:
    1) ISIN → Land
    2) Yahoo Region
    3) ETF Region
    4) Statisches Mapping
    5) Fallback: Unbekannt
    """

    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    # --- 1) ISIN prüfen ---
    isin = info.get("isin")
    if isin and len(isin) >= 2:
        prefix = isin[:2]
        if prefix in ISO_MAP:
            return ISO_MAP[prefix]

    # --- 2) Yahoo Region ---
    region = info.get("country")
    if region:
        # Normalisieren
        region = region.lower()
        if "united states" in region:
            return "USA"
        if "germany" in region:
            return "Deutschland"
        if "japan" in region:
            return "Japan"
        if "united kingdom" in region:
            return "UK"
        if "france" in region:
            return "Frankreich"

    # --- 3) ETF Region ---
    if ticker in ETF_REGIONS:
        return ETF_REGIONS[ticker]

    # --- 4) Statisches Mapping ---
    if ticker in TICKER_COUNTRY:
        return TICKER_COUNTRY[ticker]

    # --- 5) Fallback ---
    return "Unbekannt"

def map_ticker_to_country(ticker: str) -> str:
    return auto_detect_country(ticker)
