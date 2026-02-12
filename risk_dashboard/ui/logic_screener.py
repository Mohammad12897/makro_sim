#ui/logic_screener.py
import pandas as pd
from core.data.db_assets import ETF_DB, STOCK_DB


def ui_etf_screener(region, category):
    df = pd.DataFrame(ETF_DB)

    if region:
        df = df[df["Region"] == region]

    if category:
        df = df[df["Kategorie"] == category]

    if df.empty:
        return pd.DataFrame([["Keine Ergebnisse"]], columns=["Info"])

    df = df.sort_values("Volumen", ascending=False)

    return df[[
        "ISIN",
        "Name",
        "Beschreibung",
        "Region",
        "Kategorie",
        "TER",
        "Volumen",
        "Replikation",
        "TD"
    ]]

def ui_stock_screener(sector, country):
    df = pd.DataFrame(STOCK_DB)

    if sector and sector != "Alle":
        df = df[df["Sektor"] == sector]

    if country and country != "Global":
        df = df[df["Land"] == country]

    if df.empty:
        return pd.DataFrame([["Keine Ergebnisse"]], columns=["Info"])

    df = df.sort_values("KGV")

    return df[["Ticker", "Name", "Sektor", "Land", "KGV", "KUV", "PEG", "Debt/Equity", "Cashflow", "Wachstum"]]
