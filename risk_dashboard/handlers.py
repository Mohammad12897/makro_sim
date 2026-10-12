# risk_dashboard/handlers.py
import logging
import numpy as np
import pandas as pd
import streamlit as st
from risk_dashboard.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

def compute_market_values_from_prices(df: pd.DataFrame) -> pd.DataFrame:
    combined = st.session_state.get("prices_for_bt", pd.DataFrame())
    if combined.empty:
        return df
    last_prices = combined.ffill().iloc[-1]   # letzter verfügbarer Preis pro Ticker
    df = df.copy()
    def pick_price(row):
        if pd.notna(row.get("price")):
            return row["price"]
        t = normalize_ticker(row["ticker"])   # benutze deine normalize_ticker-Funktion
        return last_prices.get(t)
    df['price'] = df.apply(pick_price, axis=1)
    df['market_value'] = df['quantity'] * df['price']
    return df


def handle_holdings_analyse() -> bool:
    """
    Verarbeitet portfolio_df, validiert und persistiert.
    Gibt True zurück bei Erfolg, False bei Fehler/Abbruch.
    """
    df = st.session_state.get("portfolio_df")
    if df is None:
        st.error("Interner Fehler: portfolio_df nicht gefunden.")
        return False

    try:
        # 1) hole df aus session_state
        df = st.session_state.get("portfolio_df")
        # 2) fülle Preise falls nötig
        df = compute_market_values_from_prices(df)
        # 3) defensive Kopie und Aggregation
        df = df.copy()
        df = df.groupby("ticker", as_index=False).agg({"quantity":"sum","market_value":"sum"})
        total_mv = df["market_value"].sum()
        if total_mv == 0 or pd.isna(total_mv):
            st.error("Gesamtmarktwert ist 0 oder ungültig.")
            return False
        # 4) berechne weights etc.

        if "weight" not in df.columns:
            df["weight"] = df["market_value"] / total_mv

        # persist
        st.session_state["portfolio_df"] = df
        st.session_state["weights_by_ticker"] = dict(zip(df["ticker"], df["weight"]))
        st.session_state["portfolio_total_value"] = float(total_mv)

        # prices_for_bt defensiv setzen (falls bereits vorhanden)
        combined = st.session_state.get("prices_for_bt")
        if combined is None:
            combined = pd.DataFrame()
        st.session_state["prices_for_bt"] = combined if not combined.empty else pd.DataFrame()

        return True
    except Exception as e:
        logger.exception("handle_holdings_analyse failed: %s", e)
        st.error("Fehler bei der Verarbeitung des Portfolios.")
        return False
