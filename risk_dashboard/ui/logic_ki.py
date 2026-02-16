#ui/logic_ki.py
from __future__ import annotations

import pandas as pd

from core.engine.assets import (
    fetch_prices,
    compute_ki_score_from_prices,
)
from core.data.db_assets import ETF_DB, STOCK_DB, find_asset

def get_ki_score(ticker: str):
    """
    Einheitlicher KI‑Score für alle Assets (ETF, Aktien, Krypto, Index).
    Berechnet auf Basis von Kursdaten:
    - Momentum (6 Monate)
    - Volatilität
    - Max Drawdown
    - Sharpe‑Proxy
    """
    if not ticker:
        return None

    # Asset in DB suchen (liefert auch Yahoo‑Symbol)
    #asset, _ = find_asset(ticker)
    #yahoo = asset.get("Yahoo", ticker)

    # Kursdaten laden
    prices = fetch_prices(ticker)
    if prices is None:
        return None

    # KI‑Score berechnen
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
