#ui/logic_screener.py
from core.data.db_assets import ETF_DB, STOCK_DB, find_asset
import pandas as pd
from ui.logic_ki import get_ki_score


def ui_etf_screener(region, category):
    df = pd.DataFrame(ETF_DB)

    if region:
        df = df[df["Region"] == region]

    if category:
        df = df[df["Kategorie"] == category]

    if df.empty:
        return pd.DataFrame([["Keine Ergebnisse"]], columns=["Info"])

    # KI‑Score hinzufügen
    df["KI‑Score"] = df["Ticker"].apply(get_ki_score)

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
        "TD",
        "KI‑Score"
    ]]


def ui_stock_screener(sector, country):
    df = pd.DataFrame(STOCK_DB)

    if sector and sector != "Alle":
        df = df[df["Sektor"] == sector]

    if country and country != "Global":
        df = df[df["Land"] == country]

    if df.empty:
        return pd.DataFrame([["Keine Ergebnisse"]], columns=["Info"])

    # KI‑Score hinzufügen
    df["KI‑Score"] = df["Ticker"].apply(get_ki_score)

    df = df.sort_values("KGV")

    return df[[
        "Ticker",
        "Name",
        "Sektor",
        "Land",
        "KGV",
        "KUV",
        "PEG",
        "Debt/Equity",
        "Cashflow",
        "Wachstum",
        "KI‑Score"
    ]]
