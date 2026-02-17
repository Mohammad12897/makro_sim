#ui/logic_ki.py
from __future__ import annotations

import pandas as pd

from core.engine.assets import (
    fetch_prices,
    compute_ki_score_from_prices,
)
from core.data.db_assets import ETF_DB, STOCK_DB, find_asset

def get_ki_score(ticker: str):
    ticker = (ticker or "").strip()
    if not ticker:
        return None
    prices = fetch_prices(ticker)
    if prices is None:
        return None
    return compute_ki_score_from_prices(prices)

def build_ki_table(assets: list[dict]) -> pd.DataFrame:
    """
    Baut eine Tabelle mit KI‑Scores für Screener.
    """
    df = pd.DataFrame(assets)

    if df.empty:
        return pd.DataFrame([["Keine Ergebnisse"]], columns=["Info"])

    df["KI‑Score"] = df["Ticker"].apply(get_ki_score)

    return df.sort_values("KI‑Score", ascending=False)
