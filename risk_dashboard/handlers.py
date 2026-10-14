# risk_dashboard/handlers.py
import logging
import numpy as np
import pandas as pd
import streamlit as st
from typing import List

from risk_dashboard.ticker_utils import normalize_ticker
from risk_dashboard.utils.parsers import safe_head_preview

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
    Verarbeitet st.session_state['portfolio_df'], validiert, füllt fehlende market_value
    aus Preisen, berechnet Gewichte und persistiert Ergebnisse in session_state.
    Gibt True zurück bei Erfolg, False bei Fehler/Abbruch.
    """

    # Marker‑Liste für safe_head_preview ist extern definiert (DUMP_MARKERS)
    dump_markers: List[str] = globals().get("DUMP_MARKERS", []) or []

    def _safe_head_preview_local(df: pd.DataFrame) -> str:
        try:
            s = df.head().to_string()
        except Exception:
            s = str(df)[:1000]
        low = s.lower()
        if any(marker.lower() in low for marker in dump_markers):
            return "<skipped suspicious dump>"
        return s

    # 0) Lade portfolio_df aus Session
    df = st.session_state.get("portfolio_df")
    if df is None:
        st.error("Interner Fehler: portfolio_df nicht gefunden.")
        return False

    # Debug / Logging (sicherer Preview)
    try:
        logger.debug("handle_holdings_analyse: incoming df dtypes=%s", df.dtypes.to_dict())
        logger.debug("handle_holdings_analyse: incoming df head=%s", _safe_head_preview_local(df))
        prices_cols = list(st.session_state.get("prices_for_bt", pd.DataFrame()).columns)
        logger.debug("handle_holdings_analyse: prices_for_bt cols=%s", prices_cols)
    except Exception:
        # Logging darf nicht brechen die Verarbeitung
        logger.exception("Debug logging failed in handle_holdings_analyse")

    try:
        # 1) Defensive copy
        df = df.copy()

        # 2) Standardisiere Spaltennamen
        df.columns = [str(c).strip() for c in df.columns]
        colmap = {c.lower(): c for c in df.columns}

        # Mappe erwartete Spalten auf Standardnamen
        if "ticker" not in colmap and "symbol" not in colmap:
            st.error("CSV benötigt Spalte 'ticker' oder 'symbol'.")
            return False

        df = df.rename(columns={
            colmap.get("ticker", ""): "ticker",
            colmap.get("symbol", ""): "ticker",
            colmap.get("quantity", ""): "quantity",
            colmap.get("shares", ""): "quantity",
            colmap.get("price", ""): "price",
            colmap.get("market_value", ""): "market_value"
        })

        # 3) Normalisiere ticker und parse numerics
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
        df["quantity"] = pd.to_numeric(df.get("quantity", 0).astype(str).str.replace(",", "."), errors="coerce").fillna(0)

        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "."), errors="coerce")
        if "market_value" in df.columns:
            df["market_value"] = pd.to_numeric(df["market_value"].astype(str).str.replace(",", "."), errors="coerce")

        # 4) Versuche market_value zu berechnen, falls fehlt
        if "market_value" not in df.columns or df["market_value"].isna().any():
            if "price" in df.columns and not df["price"].isna().all():
                df["market_value"] = df["quantity"] * df["price"]
            else:
                # leave NaN for now; will try to fill from prices_for_bt below
                if "market_value" not in df.columns:
                    df["market_value"] = pd.Series([pd.NA] * len(df))

        # 5) Gruppiere nach ticker erst nachdem numerics gesetzt sind
        agg_map = {"quantity": "sum", "market_value": "sum"}
        if "price" in df.columns:
            agg_map["price"] = lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA

        df_grouped = df.groupby("ticker", as_index=False).agg(agg_map)

        # 6) Falls market_value 0 oder NaN, versuche Preise aus prices_for_bt zu holen
        df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce")
        prices = st.session_state.get("prices_for_bt", pd.DataFrame())
        if (df_grouped["market_value"].fillna(0) == 0).any() and isinstance(prices, pd.DataFrame) and not prices.empty:
            # Erzeuge Map ticker -> letzter gültiger Preis (Spaltennamen normalisiert)
            last_prices = {}
            for col in prices.columns:
                try:
                    col_norm = str(col).strip().upper()
                    last_val = prices[col].ffill().dropna()
                    if not last_val.empty:
                        last_prices[col_norm] = float(last_val.iloc[-1])
                except Exception:
                    continue

            def _fill_mv(row):
                mv = row.get("market_value")
                if pd.notna(mv) and float(mv) > 0:
                    return float(mv)
                t = str(row["ticker"]).strip().upper()
                p = last_prices.get(t)
                if p is not None:
                    return float(row.get("quantity", 0)) * float(p)
                return float(mv) if pd.notna(mv) else 0.0

            df_grouped["market_value"] = df_grouped.apply(_fill_mv, axis=1)

        # 7) Final numeric coercion and totals
        df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce").fillna(0.0)
        df_grouped["quantity"] = pd.to_numeric(df_grouped.get("quantity", 0), errors="coerce").fillna(0)

        total_mv = float(df_grouped["market_value"].sum())

        if total_mv == 0 or pd.isna(total_mv):
            st.error("Gesamtmarktwert ist 0 oder ungültig. Bitte prüfen Sie die hochgeladene Datei und die verfügbaren Preisdaten.")
            # persist grouped df anyway for inspection
            st.session_state["portfolio_df"] = df_grouped
            st.session_state["portfolio_total_value"] = float(total_mv)
            return False

        # 8) Berechne Gewichte
        df_grouped["weight"] = df_grouped["market_value"] / total_mv

        # 9) Persistiere Ergebnisse in session_state
        st.session_state["portfolio_df"] = df_grouped
        st.session_state["weights_by_ticker"] = dict(zip(df_grouped["ticker"], df_grouped["weight"]))
        st.session_state["portfolio_total_value"] = total_mv

        # 10) Defensive Sicherung von prices_for_bt in session_state
        combined = st.session_state.get("prices_for_bt")
        st.session_state["prices_for_bt"] = combined if isinstance(combined, pd.DataFrame) and not combined.empty else pd.DataFrame()

        # 11) Debug Sidebar (sichere Preview)
        try:
            st.sidebar.write("DEBUG portfolio_df head", _safe_head_preview_local(df_grouped))
            st.sidebar.write("DEBUG portfolio_df dtypes", df_grouped.dtypes.to_dict())
            st.sidebar.write("DEBUG portfolio_total_value", st.session_state.get("portfolio_total_value"))
        except Exception:
            logger.exception("Sidebar debug write failed")

        return True

    except Exception as e:
        logger.exception("handle_holdings_analyse failed: %s", e)
        st.error("Fehler bei der Verarbeitung des Portfolios.")
        return False
