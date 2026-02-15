# core/data/db_assets.py

import pandas as pd

ASSET_TEMPLATE = {
    "Ticker": None,
    "Yahoo": None,
    "ISIN": None,
    "Name": None,
    "Typ": None,
    "Region": None,
    "Sektor": None,
    "Land": None,

    # ETF-spezifisch
    "TER": None,
    "Volumen": None,
    "Replikation": None,
    "TD": None,

    # Aktien-spezifisch
    "KGV": None,
    "KUV": None,
    "PEG": None,
    "Debt/Equity": None,
    "Cashflow": None,
    "Wachstum": None,
}

def normalize_asset(asset, typ):
    normalized = ASSET_TEMPLATE.copy()
    normalized.update(asset)

    # WICHTIG: Yahoo fallback
    if not normalized.get("Yahoo"):
        normalized["Yahoo"] = normalized.get("Ticker")

    normalized["Typ"] = typ
    return normalized

ETF_DB = [
    # --- Global / World ---
    {
        "Ticker": "IWDA",
        "Yahoo": "IWDA.AS",
        "ISIN": "IE00B4L5Y983",
        "Name": "iShares Core MSCI World",
        "Region": "Global",
        "Kategorie": "Aktien",
        "TER": 0.20,
        "Volumen": 55000,
        "Replikation": "Physisch",
        "TD": -0.12
    },
    {
        "Ticker": "VWCE",
        "Yahoo": "VWCE.DE",
        "ISIN": "IE00BK5BQT80",
        "Name": "Vanguard FTSE All-World UCITS ETF",
        "Region": "Global",
        "Kategorie": "Aktien",
        "TER": 0.22,
        "Volumen": 120000,
        "Replikation": "Physisch",
        "TD": -0.10
    },
    {
        "Ticker": "SSAC",
        "Yahoo": "SSAC.L",
        "ISIN": "IE00B8KGV557",
        "Name": "iShares MSCI ACWI UCITS ETF",
        "Region": "Global",
        "Kategorie": "Aktien",
        "TER": 0.20,
        "Volumen": 18000,
        "Replikation": "Physisch",
        "TD": -0.15
    },

    # --- USA ---
    {
        "Ticker": "CSPX",
        "Yahoo": "CSPX.L",
        "ISIN": "IE00B5BMR087",
        "Name": "iShares Core S&P 500 UCITS ETF",
        "Region": "USA",
        "Kategorie": "Aktien",
        "TER": 0.07,
        "Volumen": 35000,
        "Replikation": "Physisch",
        "TD": -0.05
    },
    {
        "Ticker": "VUSA",
        "Yahoo": "VUSA.L",
        "ISIN": "IE00B3XXRP09",
        "Name": "Vanguard S&P 500 UCITS ETF",
        "Region": "USA",
        "Kategorie": "Aktien",
        "TER": 0.07,
        "Volumen": 45000,
        "Replikation": "Physisch",
        "TD": -0.04
    },

    # --- Europe ---
    {
        "Ticker": "IMEU",
        "Yahoo": "IMEU.L",
        "ISIN": "IE00B4K48X80",
        "Name": "iShares MSCI Europe UCITS ETF",
        "Region": "Europa",
        "Kategorie": "Aktien",
        "TER": 0.12,
        "Volumen": 12000,
        "Replikation": "Physisch",
        "TD": -0.18
    },
    {
        "Ticker": "VEVE",
        "Yahoo": "VEVE.L",
        "ISIN": "IE00BQQP9H09",
        "Name": "Vanguard FTSE Developed Europe UCITS ETF",
        "Region": "Europa",
        "Kategorie": "Aktien",
        "TER": 0.10,
        "Volumen": 9000,
        "Replikation": "Physisch",
        "TD": -0.12
    },

    # --- Emerging Markets ---
    {
        "Ticker": "EIMI",
        "Yahoo": "EIMI.L",
        "ISIN": "IE00BKM4GZ66",
        "Name": "iShares Core MSCI EM IMI",
        "Region": "Emerging Markets",
        "Kategorie": "Aktien",
        "TER": 0.18,
        "Volumen": 9000,
        "Replikation": "Physisch",
        "TD": -0.25
    },
    {
        "Ticker": "VFEM",
        "Yahoo": "VFEM.L",
        "ISIN": "IE00B3VVMM84",
        "Name": "Vanguard FTSE Emerging Markets UCITS ETF",
        "Region": "Emerging Markets",
        "Kategorie": "Aktien",
        "TER": 0.22,
        "Volumen": 15000,
        "Replikation": "Physisch",
        "TD": -0.20
    },

    # --- Asia / Pacific ---
    {
        "Ticker": "IAPD",
        "Yahoo": "IAPD.L",
        "ISIN": "IE00B14X4T88",
        "Name": "iShares Asia Pacific Dividend UCITS ETF",
        "Region": "Asien-Pazifik",
        "Kategorie": "Aktien",
        "TER": 0.59,
        "Volumen": 3000,
        "Replikation": "Physisch",
        "TD": -0.30
    },

    # --- Sector ETFs ---
    {
        "Ticker": "EXXT",
        "Yahoo": "EXXT.DE",
        "ISIN": "IE00B3WJKG14",
        "Name": "iShares STOXX Europe 600 Technology",
        "Region": "Europa",
        "Kategorie": "Tech",
        "TER": 0.46,
        "Volumen": 2500,
        "Replikation": "Physisch",
        "TD": -0.22
    },
    {
        "Ticker": "XLK",
        "Yahoo": "XLK",
        "ISIN": "US81369Y8030",
        "Name": "Technology Select Sector SPDR",
        "Region": "USA",
        "Kategorie": "Tech",
        "TER": 0.10,
        "Volumen": 50000,
        "Replikation": "Physisch",
        "TD": -0.03
    },

    # --- Bonds ---
    {
        "Ticker": "AGGH",
        "Yahoo": "AGGH.L",
        "ISIN": "IE00BYZ28V50",
        "Name": "iShares Core Global Aggregate Bond",
        "Region": "Global",
        "Kategorie": "Anleihen",
        "TER": 0.10,
        "Volumen": 8000,
        "Replikation": "Physisch",
        "TD": -0.12
    },
    {
        "Ticker": "VAGF",
        "Yahoo": "VAGF.L",
        "ISIN": "IE00BG47KH54",
        "Name": "Vanguard Global Aggregate Bond UCITS ETF",
        "Region": "Global",
        "Kategorie": "Anleihen",
        "TER": 0.10,
        "Volumen": 6000,
        "Replikation": "Physisch",
        "TD": -0.10
    },

    # --- Dividenden ETFs ---
    {
        "Ticker": "HDV",
        "Yahoo": "HDV",
        "ISIN": "US46429B6633",
        "Name": "iShares Core High Dividend ETF",
        "Region": "USA",
        "Kategorie": "Dividende",
        "TER": 0.08,
        "Volumen": 9000,
        "Replikation": "Physisch",
        "TD": -0.05
    },
    {
        "Ticker": "VIG",
        "Yahoo": "VIG",
        "ISIN": "US9219088443",
        "Name": "Vanguard Dividend Appreciation ETF",
        "Region": "USA",
        "Kategorie": "Dividende",
        "TER": 0.06,
        "Volumen": 70000,
        "Replikation": "Physisch",
        "TD": -0.02
    },

    # --- Immobilien ETFs ---
    {
        "Ticker": "IYR",
        "Yahoo": "IYR",
        "ISIN": "US4642877397",
        "Name": "iShares U.S. Real Estate ETF",
        "Region": "USA",
        "Kategorie": "Immobilien",
        "TER": 0.40,
        "Volumen": 5000,
        "Replikation": "Physisch",
        "TD": -0.15
    },
    {
        "Ticker": "VNQ",
        "Yahoo": "VNQ",
        "ISIN": "US9229085538",
        "Name": "Vanguard Real Estate ETF",
        "Region": "USA",
        "Kategorie": "Immobilien",
        "TER": 0.12,
        "Volumen": 35000,
        "Replikation": "Physisch",
        "TD": -0.10
    }
]



STOCK_DB = [
    {
        "Ticker": "AAPL",
        "ISIN": "US0378331005",
        "Name": "Apple",
        "Sektor": "Tech",
        "Land": "USA",
        "KGV": 28,
        "KUV": 7,
        "PEG": 2.1,
        "Debt/Equity": 1.5,
        "Cashflow": 110e9,
        "Wachstum": 0.08
    },
    {
        "Ticker": "MSFT",
        "ISIN": "US5949181045",
        "Name": "Microsoft",
        "Sektor": "Tech",
        "Land": "USA",
        "KGV": 32,
        "KUV": 10,
        "PEG": 2.3,
        "Debt/Equity": 0.6,
        "Cashflow": 95e9,
        "Wachstum": 0.10
    },
    {
        "Ticker": "SAP",
        "ISIN": "DE0007164600",
        "Name": "SAP",
        "Sektor": "Tech",
        "Land": "Deutschland",
        "KGV": 22,
        "KUV": 4,
        "PEG": 1.8,
        "Debt/Equity": 0.4,
        "Cashflow": 6e9,
        "Wachstum": 0.06
    },
    {
        "Ticker": "BAS",
        "ISIN": "DE000BASF111",
        "Name": "BASF",
        "Sektor": "Industrie",
        "Land": "Deutschland",
        "KGV": 12,
        "KUV": 0.8,
        "PEG": 1.2,
        "Debt/Equity": 0.9,
        "Cashflow": 4e9,
        "Wachstum": 0.03
    },
    {
        "Ticker": "JNJ",
        "ISIN": "US4781601046",
        "Name": "Johnson & Johnson",
        "Sektor": "Gesundheit",
        "Land": "USA",
        "KGV": 17,
        "KUV": 5,
        "PEG": 1.5,
        "Debt/Equity": 0.5,
        "Cashflow": 20e9,
        "Wachstum": 0.04
    },
    {
        "Ticker": "SPY",
        "ISIN": "US78462F1030",
        "Name": "SPDR S&P 500 ETF Trust",
        "Sektor": "Index",
        "Land": "USA",
        "KGV": None,
        "KUV": None,
        "PEG": None,
        "Debt/Equity": None,
        "Cashflow": None,
        "Wachstum": None
    }
]


STOCK_DB = [normalize_asset(a, "Stock") for a in STOCK_DB]
ETF_DB   = [normalize_asset(a, "ETF")   for a in ETF_DB]

def find_asset(identifier):
    """Sucht in ETF_DB und STOCK_DB nach Ticker, ISIN oder Yahoo."""
    identifier = identifier.upper().strip()

    # 1. ETFs durchsuchen
    for etf in ETF_DB:
        if etf.get("Ticker", "").upper() == identifier:
            return etf
        if etf.get("ISIN", "").upper() == identifier:
            return etf
        if etf.get("Yahoo", "").upper() == identifier:
            return etf

    # 2. Aktien durchsuchen
    for stock in STOCK_DB:
        if stock.get("Ticker", "").upper() == identifier:
            return stock
        if stock.get("ISIN", "").upper() == identifier:
            return stock

    return None

def detect_asset_type(identifier):
    identifier = identifier.upper().strip()

    # 1. ETFs
    for etf in ETF_DB:
        if identifier in [etf.get("Ticker", "").upper(),
                          etf.get("Yahoo", "").upper(),
                          etf.get("ISIN", "").upper()]:
            return "ETF"

    # 2. Stocks
    for stock in STOCK_DB:
        if identifier in [stock.get("Ticker", "").upper(),
                          stock.get("Yahoo", "").upper(),
                          stock.get("ISIN", "").upper()]:
            return "Stock"

    return None

CRYPTO_SYMBOLS = ["BTC", "ETH", "SOL", "ADA", "XRP"]

def detect_crypto(identifier):
    if identifier.upper() in CRYPTO_SYMBOLS:
        return "Crypto"
    return None

INDEX_SYMBOLS = ["^GSPC", "^NDX", "^DJI", "^STOXX50E"]

def detect_index(identifier):
    if identifier.upper() in INDEX_SYMBOLS:
        return "Index"
    return None

COMMODITY_SYMBOLS = ["GC=F", "CL=F", "SI=F"]

def detect_commodity(identifier):
    if identifier.upper() in COMMODITY_SYMBOLS:
        return "Commodity"
    return None


TYPE_ICONS = {
    "Stock": "📈 Aktie",
    "ETF": "🌍 ETF",
    "Crypto": "🪙 Krypto",
    "Index": "📊 Index",
    "Commodity": "⛏️ Rohstoff",
    "Unknown": "❓ Unbekannt"
}

TYPE_COLORS = {
    "Stock": "#4CAF50",      # Grün
    "ETF": "#2196F3",        # Blau
    "Crypto": "#FFC107",     # Gelb
    "Index": "#9C27B0",      # Lila
    "Commodity": "#FF5722",  # Orange
    "Unknown": "#9E9E9E"     # Grau
}

CRYPTO = {"BTC", "ETH", "SOL", "ADA", "XRP"}
INDICES = {"^GSPC", "^NDX", "^DJI", "^STOXX50E"}
COMMODITIES = {"GC=F", "CL=F", "SI=F"}

def detect_type(identifier):
    identifier = identifier.upper().strip()

    # 1. In ETF_DB?
    for etf in ETF_DB:
        if identifier in {etf.get("Ticker", "").upper(),
                          etf.get("Yahoo", "").upper(),
                          etf.get("ISIN", "").upper()}:
            return "ETF"

    # 2. In STOCK_DB?
    for stock in STOCK_DB:
        if identifier in {stock.get("Ticker", "").upper(),
                          stock.get("Yahoo", "").upper(),
                          stock.get("ISIN", "").upper()}:
            return "Stock"

    # 3. Crypto?
    if identifier in CRYPTO:
        return "Crypto"

    # 4. Index?
    if identifier in INDICES:
        return "Index"

    # 5. Commodity?
    if identifier in COMMODITIES:
        return "Commodity"

    return "Unknown"


def process_asset_input(ticker):
    if not ticker:
        return "❓ Unbekannt", TYPE_COLORS["Unknown"], {"Fehler": "Keine Eingabe"}

    ticker = ticker.strip().upper()
    asset = find_asset(ticker)
    typ = detect_type(ticker)

    # Wenn Asset nicht in DB ist → trotzdem Typ anzeigen
    if not asset:
        return TYPE_ICONS[typ], TYPE_COLORS[typ], {"Hinweis": "Asset nicht in Datenbank"}

    return TYPE_ICONS[typ], TYPE_COLORS[typ], asset
