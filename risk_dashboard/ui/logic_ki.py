#ui/logic_ki.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from core.data.db_assets import ETF_DB, STOCK_DB

def get_ki_score_for_stock(ticker):
    """
    KI‑Score für Aktien basierend auf:
    - Bewertung (KGV, KUV, PEG)
    - Verschuldung (Debt/Equity)
    - Cashflow
    - Wachstum
    """

    stock = next((s for s in STOCK_DB if s["Ticker"] == ticker), None)
    if stock is None:
        return None

    # Bewertung: niedriger = besser
    val_score = (
        max(0, 1 - stock["KGV"] / 40) * 20 +
        max(0, 1 - stock["KUV"] / 10) * 20 +
        max(0, 1 - stock["PEG"] / 3) * 20
    )

    # Verschuldung: niedriger = besser
    debt_score = max(0, 1 - stock["Debt/Equity"]) * 20

    # Cashflow: höher = besser
    cashflow_score = min(stock["Cashflow"] / 50e9, 1) * 20

    # Wachstum: höher = besser
    growth_score = min(stock["Wachstum"] / 0.15, 1) * 20

    score = val_score + debt_score + cashflow_score + growth_score
    return round(score, 3)

def get_ki_score_for_etf(ticker):
    """
    KI‑Score für ETFs basierend auf:
    - Fondsgröße (Volumen)
    - Tracking‑Differenz (TD)
    - TER
    """

    # ETF in Datenbank suchen
    etf = next((e for e in ETF_DB if e["Ticker"] == ticker or e["ISIN"] == ticker), None)
    if etf is None:
        return None

    # Normalisierung
    vol_score = min(etf["Volumen"] / 20000, 1) * 40      # große Fonds = stabil
    td_score = max(0, 1 - abs(etf["TD"])) * 30           # geringe TD = gut
    ter_score = max(0, 1 - etf["TER"]) * 30              # niedrige TER = gut

    score = vol_score + td_score + ter_score
    return round(score, 3)

def get_ki_score(ticker):
    if ticker in STOCK_DB:
        return get_ki_score_for_stock(ticker)

    etf_score = get_ki_score_for_etf(ticker)
    if etf_score is not None:
        return etf_score

    return None
