# core/data/ticker_country_map.py
# core/data/ticker_country_map.py

TICKER_COUNTRY = {
    "AAPL": "USA",
    "MSFT": "USA",
    "AMZN": "USA",
    "GOOGL": "USA",
    "META": "USA",
    "TSLA": "USA",
    "NVDA": "USA",

    "SAP.DE": "Deutschland",
    "EUNA.DE": "Deutschland",
    "4GLD.DE": "Deutschland",

    "CAC.PA": "Frankreich",
    "JPN.PA": "Japan",
    "EWJ": "Japan",
    "XDJP.DE": "Japan",

    "VUKE.L": "UK",
    "ISF.L": "UK",
    "CSUK.L": "UK",

    # usw.
}

def map_ticker_to_country(ticker: str) -> str:
    return TICKER_COUNTRY.get(ticker, "Unbekannt")
