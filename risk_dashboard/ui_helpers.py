# risk_dashboard/ui_helpers.py
from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path
import streamlit as st
import logging


from core.yf_helper import _safe_read_csv_text
from risk_dashboard.data_utils import find_price_for_ticker, normalize_ticker, fetch_last_prices, safe_rerun
from risk_dashboard.time_utils import _harmonize_index_tz, _make_index_naive
from risk_dashboard.price_utils import _pick_price_column, _extract_price_series_from_yf
from risk_dashboard.data_utils import fetch_prices_for_ticker, normalize_prices
logger = logging.getLogger(__name__)


# --- Helpers ---
@st.cache_data
def load_markdown_safe(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")

def status_legend():
    c1, c2, c3 = st.columns([1,6,6])
    with c1:
        st.markdown("<span style='color:green; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**iShares (UK/US)** – echte Holdings verfügbar")
    with c3:
        st.markdown("")
    st.markdown("---")
    c1, c2 = st.columns([1,10])
    with c1:
        st.markdown("<span style='color:orange; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**Vanguard / Amundi / Xtrackers** – Demo‑Holdings")
    c1, c2 = st.columns([1,10])
    with c1:
        st.markdown("<span style='color:red; font-size:18px;'>●</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**Cash / Nicht‑ETF** – keine Holdings")

def show_intro(md_path: str):
    md = load_markdown_safe(md_path)
    if md:
        with st.expander("Einführung", expanded=True):
            st.markdown(md, unsafe_allow_html=False)
    else:
        st.info("Einführungsdokument nicht gefunden.")

def handle_portfolio_upload_with_price_lookup(prefix="profile"):
    uploader_key = f"portfolio_uploader_{prefix}"
    uploaded = st.file_uploader(
        "Portfolio CSV (ticker, quantity, price or market_value)",
        type=["csv"],
        key=uploader_key
    )

    if uploaded is None:
        return None

    try:
        Path("data/holdings").mkdir(parents=True, exist_ok=True)
        with open("data/holdings/portfolio.csv", "wb") as f:
            f.write(uploaded.getbuffer())

        # robustes Einlesen: versuche pd.read_csv, sonst _safe_read_csv_text
        uploaded.seek(0)
        try:
            df = pd.read_csv(uploaded)
        except Exception:
            uploaded.seek(0)
            text = uploaded.read()
            df = _safe_read_csv_text(text)
            if df is None:
                st.error("Konnte die Datei nicht als CSV/TSV einlesen.")
                return None

        # normalize column names and map variants
        df.columns = [str(c).strip() for c in df.columns]
        colmap = {c.lower(): c for c in df.columns}

        if "ticker" not in colmap and "symbol" not in colmap:
            st.error("CSV benötigt Spalte 'ticker' oder 'symbol'.")
            return None

        df = df.rename(columns={
            colmap.get("ticker",""): "ticker",
            colmap.get("symbol",""): "ticker",
            colmap.get("quantity",""): "quantity",
            colmap.get("shares",""): "quantity",
            colmap.get("price",""): "price",
            colmap.get("market_value",""): "market_value"
        })

        # numeric parsing: replace comma decimals and coerce
        if "quantity" in df.columns:
            df["quantity"] = pd.to_numeric(df["quantity"].astype(str).str.replace(",", "."), errors="coerce")
        else:
            df["quantity"] = 0

        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "."), errors="coerce")
        if "market_value" in df.columns:
            df["market_value"] = pd.to_numeric(df["market_value"].astype(str).str.replace(",", "."), errors="coerce")

        # compute market_value if missing
        if "market_value" not in df.columns or df["market_value"].isna().any():
            if "price" in df.columns and not df["price"].isna().all():
                df["market_value"] = df["quantity"] * df["price"]
            else:
                # keep rows with market_value only if present; otherwise try to fill later from prices_for_bt
                df["market_value"] = df.get("market_value", pd.Series(dtype=float))

        # drop rows without ticker or quantity
        df = df.dropna(subset=["ticker"])
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

        # If market_value still missing for all rows, we allow it and rely on compute_market_values_from_prices
        # aggregate quantities and market_value where present
        df = df.groupby("ticker", as_index=False).agg({
            "quantity": "sum",
            "price": lambda s: pd.to_numeric(s, errors="coerce").dropna().iloc[0] if s.dropna().any() else pd.NA,
            "market_value": "sum"
        })

        # persist cleaned df once
        st.session_state["portfolio_df"] = df

        # If prices_for_bt exists, compute market values from prices; otherwise handle_holdings_analyse will try
        from risk_dashboard.handlers import handle_holdings_analyse
        ok = handle_holdings_analyse()
        if ok:
            st.session_state["navigate_to"] = "Holdings Analyse"
            from risk_dashboard.data_utils import safe_rerun
            safe_rerun(stop=False)

        st.success(f"Portfolio geladen: {len(df)} Positionen, Gesamtwert {st.session_state.get('portfolio_total_value', 'n/a')}")
        st.write(df)
        return df

    except Exception as e:
        logger.exception("Fehler beim Upload/Verarbeiten: %s", e)
        st.error(f"Fehler beim Einlesen: {e}")
        return None


def add_new_tickers_to_portfolio(new_tickers: List[str], default_qty: int = 1):
    """
    Fügt Ticker mit default_qty in st.session_state['portfolio_df'] ein.
    new_tickers: List[str] (z. B. ['AAPL', 'CSPX.L'])
    """
    if not new_tickers:
        return

    # normalize input tickers
    new_tickers_norm = [normalize_ticker(str(t)) for t in new_tickers if t and str(t).strip()]
    if not new_tickers_norm:
        return

    # ensure portfolio_df exists and has correct columns/types
    portfolio = st.session_state.get("portfolio_df")
    if portfolio is None or portfolio.empty:
        portfolio = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # normalize existing tickers and ensure dtypes
    portfolio = portfolio.copy()
    if "ticker" not in portfolio.columns:
        portfolio["ticker"] = ""
    portfolio["ticker"] = portfolio["ticker"].astype(str).str.strip().str.upper()
    if "quantity" not in portfolio.columns:
        portfolio["quantity"] = 0
    portfolio["quantity"] = pd.to_numeric(portfolio["quantity"], errors="coerce").fillna(0).astype(int)

    # build list of tickers to actually add (avoid duplicates)
    existing_set = set(portfolio["ticker"].tolist())
    to_add = [t for t in new_tickers_norm if t and t.upper() not in existing_set]

    if not to_add:
        # nothing to add
        st.info("Keine neuen Ticker zum Hinzufügen.")
        st.session_state["portfolio_df"] = portfolio
        return

    # create DataFrame for new rows with correct dtypes
    new_rows = pd.DataFrame([{"ticker": t.upper(), "quantity": int(default_qty), "price": pd.NA, "market_value": pd.NA, "weight": pd.NA} for t in to_add])
    # ensure dtypes
    new_rows["ticker"] = new_rows["ticker"].astype(str)
    new_rows["quantity"] = pd.to_numeric(new_rows["quantity"], errors="coerce").fillna(0).astype(int)

    # append and consolidate
    portfolio = pd.concat([portfolio, new_rows], ignore_index=True)
    portfolio = portfolio.groupby(portfolio["ticker"].astype(str).str.strip().str.upper(), as_index=False).agg({
        "quantity": "sum",
        "price": lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA,
        "market_value": "sum",
        "weight": "first"
    })

    # persist
    st.session_state["portfolio_df"] = portfolio
    st.success(f"{len(to_add)} neue Ticker hinzugefügt.")
    return

def add_new_tickers_to_portfolio_with_quantities(pairs: List[Tuple[str,int]], default_qty: int = 1):
    """
    pairs: list of (ticker, qty)
    """
    if not pairs:
        return

    # normalize pairs
    pairs_norm = [(normalize_ticker(str(t)).upper(), int(q) if q is not None else int(default_qty)) for t,q in pairs]

    portfolio = st.session_state.get("portfolio_df")
    if portfolio is None or portfolio.empty:
        portfolio = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    portfolio = portfolio.copy()
    if "ticker" not in portfolio.columns:
        portfolio["ticker"] = ""
    portfolio["ticker"] = portfolio["ticker"].astype(str).str.strip().str.upper()
    if "quantity" not in portfolio.columns:
        portfolio["quantity"] = 0
    portfolio["quantity"] = pd.to_numeric(portfolio["quantity"], errors="coerce").fillna(0).astype(int)

    # append each pair
    new_rows = []
    for t, q in pairs_norm:
        if t in portfolio["ticker"].values:
            portfolio.loc[portfolio["ticker"] == t, "quantity"] += int(q)
        else:
            new_rows.append({"ticker": t, "quantity": int(q), "price": pd.NA, "market_value": pd.NA, "weight": pd.NA})

    if new_rows:
        portfolio = pd.concat([portfolio, pd.DataFrame(new_rows)], ignore_index=True)

    portfolio = portfolio.groupby(portfolio["ticker"].astype(str).str.strip().str.upper(), as_index=False).agg({
        "quantity": "sum",
        "price": lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA,
        "market_value": "sum",
        "weight": "first"
    })

    st.session_state["portfolio_df"] = portfolio
    st.success(f"{len(pairs_norm)} Ticker verarbeitet.")
    return

def consolidate_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereinigt und konsolidiert portfolio_df:
    - Normalisiert ticker (Uppercase, trim)
    - Entfernt angehängte Mengenreste (z. B. 'DAX 3' -> 'DAX')
    - Gruppiert nach ticker, summiert quantity und market_value
    - Rechnet weight neu
    """
    if df is None or df.empty:
        # Gib ein leeres DataFrame mit Standardspalten zurück
        return pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    df = df.copy()

    # 1) Normalisiere ticker
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["ticker"] = df["ticker"].str.split().str[0]  # 'DAX 3' -> 'DAX'

    # 2) Stelle sicher, dass die erwarteten Spalten existieren
    expected_cols = {
        "quantity": 0,
        "market_value": 0.0,
        "price": None
    }
    for col, default in expected_cols.items():
        if col not in df.columns:
            df[col] = default

    # 3) Typkonvertierung mit Fallbacks
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0.0)

    # 4) Gruppieren: nur existierende Spalten in agg verwenden
    agg_map = {}
    if "quantity" in df.columns:
        agg_map["quantity"] = "sum"
    if "market_value" in df.columns:
        agg_map["market_value"] = "sum"
    # price: last if present
    if "price" in df.columns:
        agg_map["price"] = "last"

    # Falls agg_map leer wäre (sehr unwahrscheinlich), lege Standardaggregation an
    if not agg_map:
        agg_map = {"quantity": "sum", "market_value": "sum", "price": "last"}

    df_grouped = df.groupby("ticker", as_index=False).agg(agg_map)

    # 5) Recompute weights
    total_mv = df_grouped.get("market_value", pd.Series([0.0])).sum()
    if total_mv > 0:
        df_grouped["weight"] = (df_grouped["market_value"] / total_mv) * 100.0
    else:
        df_grouped["weight"] = 0.0

    # 6) Sicherstellen, dass alle Spalten in der erwarteten Reihenfolge vorhanden sind
    cols = ["ticker", "quantity", "price", "market_value", "weight"]
    for c in cols:
        if c not in df_grouped.columns:
            df_grouped[c] = None if c == "price" else 0.0

    return df_grouped[cols]


def add_tickers_and_fetch(tickers_with_qty, prefix="etf", start=None, end=None):
    qty_map = {}
    if tickers_with_qty and isinstance(tickers_with_qty[0], (list, tuple)):
        tickers = [str(t).strip().upper() for t, _ in tickers_with_qty]
        qty_map = {str(t).strip().upper(): int(q) for t, q in tickers_with_qty}
    else:
        tickers = [str(t).strip().upper() for t in tickers_with_qty] if tickers_with_qty else []

    success = []
    failed = []
    prices_accum = {}

    for t in tickers:
        if not t:
            continue
        try:
            df = fetch_prices_for_ticker(t, start=start, end=end, auto_adjust=True, threads=False)
        except Exception:
            logger.exception("add_tickers_and_fetch: fetch_prices_for_ticker raised for %s", t)
            failed.append(t)
            continue

        if df is None or (hasattr(df, "empty") and df.empty):
            failed.append(t)
            logger.debug("add_tickers_and_fetch: no data for %s", t)
            continue

        try:
            df_norm = normalize_prices(df)
        except Exception:
            logger.exception("add_tickers_and_fetch: normalize_prices failed for %s", t)
            failed.append(t)
            continue

        if df_norm is None or (hasattr(df_norm, "empty") and df_norm.empty):
            failed.append(t)
            logger.debug("add_tickers_and_fetch: normalized empty for %s", t)
            continue

        # pick sensible column and set normalized series name
        try:
            col = _pick_price_column(df_norm)
            series = df_norm[col].copy()
            series.name = normalize_ticker(t)
            prices_accum[series.name] = series
            success.append(t)
        except Exception:
            logger.exception("add_tickers_and_fetch: error selecting price series for %s", t)
            failed.append(t)
            continue

    # Build combined DataFrame from accumulated series (dict of Series -> clean columns)
    combined = pd.DataFrame()
    if prices_accum:
        try:
            combined = pd.concat(prices_accum, axis=1)
            # ensure simple string column names
            if isinstance(combined.columns, pd.MultiIndex):
                combined.columns = ["_".join(map(str, c)).strip() for c in combined.columns]
            else:
                combined.columns = [str(c).strip() for c in combined.columns]
        except Exception:
            try:
                combined = pd.DataFrame(prices_accum)
            except Exception:
                logger.exception("add_tickers_and_fetch: failed to build combined DataFrame")
                combined = pd.DataFrame()

    # Persist user_tickers
    st.session_state.setdefault("user_tickers", [])
    for t in success:
        if t not in st.session_state["user_tickers"]:
            st.session_state["user_tickers"].append(t)

    # Merge into existing prices_for_bt (harmonize tz first)
    existing = st.session_state.get("prices_for_bt")
    if existing is None or (hasattr(existing, "empty") and existing.empty):
        st.session_state["prices_for_bt"] = combined
    else:
        existing = st.session_state.get("prices_for_bt", pd.DataFrame())

        # If combined contains OHLC multi-columns, extract price series
        combined = _extract_price_series_from_yf(combined, prefer="ADJ CLOSE")

        # Harmonize tz (recommended: UTC)
        existing = _harmonize_index_tz(existing, target_tz="UTC")
        combined = _harmonize_index_tz(combined, target_tz="UTC")

        # sort indices
        try:
            existing = existing.sort_index()
            combined = combined.sort_index()
        except Exception:
            pass

        # attempt concat, with fallback to making indices naive if tz mismatch persists
        try:
            merged = pd.concat([existing, combined], axis=1)
        except TypeError as e:
            logger.warning("Concat TypeError, trying naive fallback: %s", e)
            try:
                existing = _make_index_naive(existing)
                combined = _make_index_naive(combined)
                merged = pd.concat([existing, combined], axis=1)
            except Exception as e2:
                logger.error("add_tickers_and_fetch: merging prices_for_bt failed after fallback: %s; replacing with combined", e2)
                st.session_state["prices_for_bt"] = combined
                merged = None

        if merged is not None:
            merged = merged.loc[:, ~merged.columns.duplicated()]
            st.session_state["prices_for_bt"] = merged

    # Update portfolio quantities from qty_map
    if qty_map:
        portfolio = st.session_state.get("portfolio")
        if portfolio is None or portfolio.empty:
            portfolio = pd.DataFrame(columns=["ticker", "quantity"])
        # ensure types
        if "ticker" not in portfolio.columns:
            portfolio["ticker"] = portfolio.get("ticker", pd.Series(dtype=str))
        if "quantity" not in portfolio.columns:
            portfolio["quantity"] = portfolio.get("quantity", pd.Series(dtype=int))
        portfolio["ticker"] = portfolio["ticker"].astype(str)
        portfolio["quantity"] = pd.to_numeric(portfolio["quantity"], errors="coerce").fillna(0).astype(int)

        for t in success:
            q = int(qty_map.get(t, 1))
            if t in portfolio["ticker"].values:
                portfolio.loc[portfolio["ticker"] == t, "quantity"] += q
            else:
                new_row = pd.DataFrame([{"ticker": t, "quantity": q}])
                portfolio = pd.concat([portfolio, new_row], ignore_index=True)

        portfolio = portfolio.groupby("ticker", as_index=False).agg({"quantity": "sum"})
        st.session_state["portfolio"] = portfolio

    # final_df: what we actually stored
    final_df = st.session_state.get("prices_for_bt", combined)

    # debug tz info
    try:
        logger.debug("prices_for_bt index tz=%s combined index tz=%s",
                     getattr(final_df.index, "tz", None),
                     getattr(combined.index, "tz", None))
    except Exception:
        pass

    return success, failed, final_df

def persist_portfolio_df(df: pd.DataFrame):
    # normalize columns
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0).astype(int)
    for col in ("price","market_value","weight"):
        if col not in df.columns:
            df[col] = None
    st.session_state["portfolio_df"] = df[["ticker","quantity","price","market_value","weight"]]

