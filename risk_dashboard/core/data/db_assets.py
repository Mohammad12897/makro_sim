# core/data/db_assets.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.engine.assets import (
    fetch_prices,
    compute_ki_score_from_prices,
    compute_radar_data,
    render_type_html,
)

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

ETF_DB: List[Dict[str, Any]] = [
    # --- Global / World ---
    {
        "Ticker": "IWDA",
        "Yahoo": "IWDA.AS",
        "ISIN": "IE00B4L5Y983",
        "Name": "iShares Core MSCI World",
        "Region": "Global",
        "Kategorie": "Aktien",
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
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
        "Typ": "ETF",
        "TER": 0.12,
        "Volumen": 35000,
        "Replikation": "Physisch",
        "TD": -0.10
    }
]



STOCK_DB: List[Dict[str, Any]] = [
    {
        "Ticker": "AAPL",
        "Yahoo": "AAPL",
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
        "Yahoo": "MSFT",
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
        "Yahoo": "SAP",
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
        "Yahoo": "BAS",
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
        "Yahoo": "JNJ",
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
        "Yahoo": "SPY",
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


def _find_in_db(ticker: str, db: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    t = ticker.strip().upper()
    for row in db:
        if row.get("Ticker", "").upper() == t:
            return row
    return None


def detect_type(asset: Dict[str, Any]) -> str:
    t = (asset.get("Typ") or "").strip().lower()
    if t in {"etf", "stock", "crypto", "index"}:
        return t.capitalize()
    # Fallback: aus Kategorie ableiten
    kat = (asset.get("Kategorie") or "").strip().lower()
    if kat == "aktien":
        return "Stock"
    return "Unknown"

def type_color(typ: str) -> Tuple[str, str]:
    t = (typ or "Unknown").strip().lower()
    mapping = {
        "etf": ("ETF", "#2563eb"),
        "stock": ("Aktie", "#16a34a"),
        "crypto": ("Krypto", "#f97316"),
        "index": ("Index", "#7c3aed"),
    }
    return mapping.get(t, ("Unbekannt", "#6b7280"))

def find_asset(ticker: str):
    """
    Sucht ein Asset in ETF_DB / STOCK_DB.
    Gibt (asset_dict, typ_string) zurück.
    """
    asset = _find_in_db(ticker, ETF_DB)
    if asset is not None:
        return asset, "ETF"

    asset = _find_in_db(ticker, STOCK_DB)
    if asset is not None:
        return asset, "Stock"

    # Fallback: Minimal-Asset
    return {"Ticker": ticker, "Name": ticker, "Typ": "Unknown"}, "Unknown"


def get_ki_score(ticker: str):
    """
    Wrapper für Screener: lädt Kurse und berechnet KI-Score.
    """
    prices = fetch_prices(ticker)
    if prices is None:
        return None
    return compute_ki_score_from_prices(prices)

def get_asset_full_profile(ticker: str) -> Dict[str, Any]:
    """
    Liefert ein vollständiges Profil:
    - Stammdaten (aus DB)
    - Preise
    - KI-Score
    - Radar-Daten
    """
    asset, typ = find_asset(ticker)
    yahoo = asset.get("Yahoo", asset.get("Ticker", ticker))

    prices = fetch_prices(yahoo)
    ki_score = compute_ki_score_from_prices(prices) if prices is not None else None
    radar = compute_radar_data(asset, prices, typ)

    profile: Dict[str, Any] = {
        "asset": asset,
        "typ": typ,
        "yahoo": yahoo,
        "prices": prices,
        "ki_score": ki_score,
        "radar": radar,
    }
    return profile


def process_asset_input(ticker: str) -> Tuple[str, str, Dict[str, Any], Optional[float], Dict[str, Optional[float]]]:
    """
    Nimmt einen Ticker entgegen und gibt zurück:
    - typ_text (z. B. 'ETF')
    - color (Hex)
    - asset (dict)
    - ki_score (float | None)
    - radar (dict)
    """
    profile = get_asset_full_profile(ticker)
    asset = profile["asset"]
    typ = detect_type(asset)
    typ_text, color = type_color(typ)

    return typ_text, color, asset, profile["ki_score"], profile["radar"]



def ui_wrapper(ticker: str):
    """
    Wrapper für Gradio:
    Gibt zurück:
    - HTML-Badge
    - Asset-Daten (dict)
    - KI-Score
    - Radar-Daten
    """
    ticker = (ticker or "").strip()
    if not ticker:
        return (
            "<span style='color:#6b7280;'>Bitte einen Ticker eingeben.</span>",
            {},
            None,
            {}
        )

    typ_text, color, asset, ki_score, radar = process_asset_input(ticker)
    html = render_type_html(typ_text, color)

    return html, asset, ki_score, radar
