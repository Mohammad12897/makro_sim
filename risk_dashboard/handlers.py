# risk_dashboard/handlers.py
import logging
import re
import numpy as np
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional

from risk_dashboard.ticker_utils import normalize_ticker
from risk_dashboard.utils.parsers import safe_head_preview, DUMP_MARKERS

logger = logging.getLogger(__name__)

def compute_market_values_from_prices(df: pd.DataFrame) -> pd.DataFrame:
    prices = st.session_state.get("prices_for_bt", pd.DataFrame())
    if prices is None or prices.empty:
        return df

    from risk_dashboard.price_utils import build_last_price_map
    from risk_dashboard.ticker_utils import normalize_ticker_simple

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).apply(normalize_ticker_simple)
    df["quantity"] = pd.to_numeric(df.get("quantity", 0).astype(str).str.replace(",", "."), errors="coerce").fillna(0)
    df["price"] = pd.to_numeric(df.get("price", pd.Series(dtype=float)).astype(str).str.replace(",", "."), errors="coerce")
    df["market_value"] = pd.to_numeric(df.get("market_value", pd.Series(dtype=float)), errors="coerce")

    # compute market_value from price if possible
    if df["market_value"].isna().any():
        df["market_value"] = df["market_value"].fillna(df["quantity"] * df["price"])

    # fill remaining missing market_values using last prices from prices_for_bt
    missing_mask = df["market_value"].isna() | (df["market_value"] == 0)
    if missing_mask.any():
        tickers = df.loc[missing_mask, "ticker"].astype(str).unique().tolist()
        last_prices = build_last_price_map(prices, tickers, normalize_ticker_simple)
        def _fill(row):
            if pd.notna(row["market_value"]) and float(row["market_value"]) > 0:
                return float(row["market_value"])
            p = last_prices.get(normalize_ticker_simple(row["ticker"]))
            if p is not None:
                return float(row["quantity"]) * float(p)
            return 0.0
        df.loc[missing_mask, "market_value"] = df.loc[missing_mask].apply(_fill, axis=1)

    # set price from market_value/quantity if price missing
    price_missing = df["price"].isna() & (df["quantity"] > 0)
    df.loc[price_missing, "price"] = df.loc[price_missing].apply(lambda r: (r["market_value"] / r["quantity"]) if r["quantity"] else pd.NA, axis=1)

    return df

def handle_holdings_analyse() -> bool:
    """
    Verarbeitet st.session_state['portfolio_df'], validiert, füllt fehlende market_value
    aus Preisen, berechnet Gewichte und persistiert Ergebnisse in session_state.
    Gibt True zurück bei Erfolg, False bei Fehler/Abbruch.
    """
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

    df = st.session_state.get("portfolio_df")
    if df is None:
        st.error("Interner Fehler: portfolio_df nicht gefunden.")
        return False

    try:
        logger.debug("handle_holdings_analyse: incoming df dtypes=%s", df.dtypes.to_dict())
        logger.debug("handle_holdings_analyse: incoming df head=%s", _safe_head_preview_local(df))
        prices_cols = list(st.session_state.get("prices_for_bt", pd.DataFrame()).columns)
        logger.debug("handle_holdings_analyse: prices_for_bt cols=%s", prices_cols)
    except Exception:
        logger.exception("Debug logging failed in handle_holdings_analyse")

    try:
        # defensive copy
        df = df.copy()

        # normalize column names and map synonyms
        df.columns = [str(c).strip() for c in df.columns]
        colmap = {c.lower(): c for c in df.columns}
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

        # keep original ticker for display, create normalized key
        df["ticker"] = df["ticker"].astype(str).str.strip()
        df["ticker_norm"] = df["ticker"].str.upper()

        # numeric parsing
        df["quantity"] = pd.to_numeric(df.get("quantity", 0).astype(str).str.replace(",", "."), errors="coerce").fillna(0)
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "."), errors="coerce")
        if "market_value" in df.columns:
            df["market_value"] = pd.to_numeric(df["market_value"].astype(str).str.replace(",", "."), errors="coerce")

        # compute market_value if price present
        if "market_value" not in df.columns or df["market_value"].isna().any():
            if "price" in df.columns and not df["price"].isna().all():
                df["market_value"] = df["quantity"] * df["price"]
            else:
                if "market_value" not in df.columns:
                    df["market_value"] = pd.Series([pd.NA] * len(df))

        # aggregate by normalized ticker
        agg_map = {"quantity": "sum", "market_value": "sum"}
        if "price" in df.columns:
            agg_map["price"] = lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA

        df_grouped = df.groupby("ticker_norm", as_index=False).agg(agg_map)
        df_grouped = df_grouped.rename(columns={"ticker_norm": "ticker"})
        df_grouped["ticker"] = df_grouped["ticker"].astype(str).str.upper()

        # fill missing market_value from prices_for_bt
        df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce")
        prices = st.session_state.get("prices_for_bt", pd.DataFrame())

        # Debug: show tickers and price columns at function entry
        logger.debug("ENTER handle_holdings_analyse: portfolio_df tickers=%s", list(df['ticker'].astype(str).str.upper().unique()))
        logger.debug("ENTER handle_holdings_analyse: prices_for_bt cols=%s", None if prices is None else list(prices.columns))

        if (df_grouped["market_value"].fillna(0) == 0).any() and isinstance(prices, pd.DataFrame) and not prices.empty:
            # build latest price map (uppercase keys) with simplified token fallback
            last_prices: Dict[str, Optional[float]] = {}

            # actual column names from prices (may already be uppercased)
            price_cols_actual = list(prices.columns)

            # create mapping col_upper -> last_value
            for col in price_cols_actual:
                try:
                    col_up = str(col).strip().upper()
                    # get series safely (handle if prices has unexpected structure)
                    series = prices[col] if col in prices.columns else prices.loc[:, prices.columns.str.upper() == col_up]
                    if isinstance(series, pd.DataFrame):
                        series = series.iloc[:, 0]
                    last_val_series = series.ffill().dropna()
                    last_prices[col_up] = float(last_val_series.iloc[-1]) if not last_val_series.empty else None
                except Exception:
                    last_prices[col_up] = None

                # also add simplified token (remove suffixes like -USD, .DE, _XXX)
                simple = re.sub(r'[-\._].*$', '', col_up)
                if simple and simple not in last_prices:
                    last_prices[simple] = last_prices[col_up]

            logger.debug("handle_holdings_analyse: last_prices sample=%s", {k: last_prices[k] for k in list(last_prices)[:10]})

            def _fill_mv(row):
                mv = row.get("market_value")
                try:
                    if pd.notna(mv) and float(mv) > 0:
                        return float(mv)
                except Exception:
                    pass
                t = str(row["ticker"]).strip().upper()
                p = last_prices.get(t)
                if p is not None:
                    return float(row.get("quantity", 0)) * float(p)
                # prefix/suffix fallback (e.g., BTC -> BTC-USD)
                for col_key, val in last_prices.items():
                    if val is None:
                        continue
                    if col_key.startswith(t) or t.startswith(col_key):
                        return float(row.get("quantity", 0)) * float(val)
                return 0.0

            df_grouped["market_value"] = df_grouped.apply(_fill_mv, axis=1)

        # final coercion
        df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce").fillna(0.0)
        df_grouped["quantity"] = pd.to_numeric(df_grouped.get("quantity", 0), errors="coerce").fillna(0)

        total_mv = float(df_grouped["market_value"].sum())

        if total_mv == 0 or pd.isna(total_mv):
            st.error("Gesamtmarktwert ist 0 oder ungültig. Bitte prüfen Sie die hochgeladene Datei und die verfügbaren Preisdaten.")
            st.session_state["portfolio_df"] = df_grouped
            logger.debug("persisting portfolio_df columns=%s head=%s", list(df_grouped.columns), safe_head_preview(df_grouped, DUMP_MARKERS))
            st.session_state["portfolio_total_value"] = float(total_mv)
            return False

        # compute weights and persist
        df_grouped["weight"] = df_grouped["market_value"] / total_mv
        st.session_state["portfolio_df"] = df_grouped
        logger.debug("persisting portfolio_df columns=%s head=%s", list(df_grouped.columns), safe_head_preview(df_grouped, DUMP_MARKERS))
        st.session_state["weights_by_ticker"] = dict(zip(df_grouped["ticker"], df_grouped["weight"]))
        st.session_state["portfolio_total_value"] = total_mv

        # defensive preview of prices_for_bt
        combined = st.session_state.get("prices_for_bt")
        logger.debug("prices_for_bt type=%s shape=%s cols=%s", type(combined), getattr(combined,'shape',None), list(getattr(combined,'columns',[])))
        if isinstance(combined, pd.DataFrame) and not combined.empty:
            logger.debug("prices_for_bt sample=%s", safe_head_preview(combined, DUMP_MARKERS))
        st.session_state["prices_for_bt"] = combined if isinstance(combined, pd.DataFrame) and not combined.empty else pd.DataFrame()

        # sidebar debug
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
