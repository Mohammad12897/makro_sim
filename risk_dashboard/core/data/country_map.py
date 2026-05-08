# core/data/country_map.py

COUNTRY_MAP = {
    "Deutschland (DAX)": "^GDAXI",
    "USA (S&P 500)": "^GSPC",
    "UK (FTSE 100)": "^FTSE",
    "Japan (Nikkei 225)": "^N225",
    "Hongkong (Hang Seng)": "^HSI"
}

def get_country_choices():
    return list(COUNTRY_MAP.keys())

def resolve_country(name):
    return COUNTRY_MAP[name]
