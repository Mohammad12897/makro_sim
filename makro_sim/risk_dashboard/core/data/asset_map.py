#core/data/asset_map.py
ASSET_MAP = {
    "deutschland": "^GDAXI",
    "usa": "^GSPC",
    "japan": "^N225",
    "gold": "GC=F",
    "s&p": "^GSPC",
    "sp500": "^GSPC",
    "bund": "BUND.DE",
}

def resolve_asset(name_or_ticker: str) -> str:
    key = name_or_ticker.strip().lower()
    return ASSET_MAP.get(key, name_or_ticker)
