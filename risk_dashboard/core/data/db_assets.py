# core/data/db_assets.py

import pandas as pd

ETF_DB = [
    {"ISIN": "IE00B4L5Y983", "Name": "iShares Core MSCI World", "Region": "Global", "Kategorie": "Aktien", "TER": 0.20, "Volumen": 55000, "Replikation": "Physisch", "TD": -0.12},
    {"ISIN": "IE00B5BMR087", "Name": "Vanguard FTSE All-World", "Region": "Global", "Kategorie": "Aktien", "TER": 0.22, "Volumen": 110000, "Replikation": "Physisch", "TD": -0.10},
    {"ISIN": "IE00B3XXRP09", "Name": "iShares S&P 500", "Region": "USA", "Kategorie": "Aktien", "TER": 0.07, "Volumen": 45000, "Replikation": "Physisch", "TD": -0.05},
    {"ISIN": "IE00B4WXJJ64", "Name": "iShares MSCI Europe", "Region": "Europa", "Kategorie": "Aktien", "TER": 0.12, "Volumen": 12000, "Replikation": "Physisch", "TD": -0.18},
    {"ISIN": "IE00B5M4WH52", "Name": "iShares EM IMI", "Region": "Emerging Markets", "Kategorie": "Aktien", "TER": 0.18, "Volumen": 9000, "Replikation": "Physisch", "TD": -0.25},
    {
        "Ticker": "EIMI",
        "Yahoo": "EIMI.L",
        "ISIN": "IE00BKM4GZ66",
        "Name": "iShares Core MSCI EM IMI",
        "Beschreibung": "Breit gestreuter Emerging-Markets-ETF mit physischer Replikation.",
        "Region": "Emerging Markets",
        "Kategorie": "Aktien",
        "TER": 0.18,
        "Volumen": 9000,
        "Replikation": "Physisch",
        "TD": -0.25
    },
    {
        "Ticker": "VWCE",
        "Yahoo": "VWCE.DE",
        "ISIN": "IE00BK5BQT80",
        "Name": "Vanguard FTSE All-World UCITS ETF",
        "Beschreibung": "Globaler ETF mit über 3500 Aktien weltweit.",
        "Region": "Global",
        "Kategorie": "Aktien",
        "TER": 0.22,
        "Volumen": 12000,
        "Replikation": "Physisch",
        "TD": -0.15
    },
    {
        "Ticker": "CSPX",
        "Yahoo": "CSPX.L",
        "ISIN": "IE00B5BMR087",
        "Name": "iShares Core S&P 500 UCITS ETF",
        "Beschreibung": "S&P 500 ETF mit physischer Replikation.",
        "Region": "USA",
        "Kategorie": "Aktien",
        "TER": 0.07,
        "Volumen": 35000,
        "Replikation": "Physisch",
        "TD": -0.05
    }

]

STOCK_DB = [
    {"Ticker": "AAPL", "Name": "Apple", "Sektor": "Tech", "Land": "USA", "KGV": 28, "KUV": 7, "PEG": 2.1, "Debt/Equity": 1.5, "Cashflow": 110e9, "Wachstum": 0.08},
    {"Ticker": "MSFT", "Name": "Microsoft", "Sektor": "Tech", "Land": "USA", "KGV": 32, "KUV": 10, "PEG": 2.3, "Debt/Equity": 0.6, "Cashflow": 95e9, "Wachstum": 0.10},
    {"Ticker": "SAP", "Name": "SAP", "Sektor": "Tech", "Land": "Deutschland", "KGV": 22, "KUV": 4, "PEG": 1.8, "Debt/Equity": 0.4, "Cashflow": 6e9, "Wachstum": 0.06},
    {"Ticker": "BAS", "Name": "BASF", "Sektor": "Industrie", "Land": "Deutschland", "KGV": 12, "KUV": 0.8, "PEG": 1.2, "Debt/Equity": 0.9, "Cashflow": 4e9, "Wachstum": 0.03},
    {"Ticker": "JNJ", "Name": "Johnson & Johnson", "Sektor": "Gesundheit", "Land": "USA", "KGV": 17, "KUV": 5, "PEG": 1.5, "Debt/Equity": 0.5, "Cashflow": 20e9, "Wachstum": 0.04},
]
