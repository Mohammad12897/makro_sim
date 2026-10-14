# risk_dashboard/ui_helpers.py
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
import streamlit as st
import tempfile
import logging


from risk_dashboard.core.yf_helper import _safe_read_csv_text
from risk_dashboard.data_utils import find_price_for_ticker, fetch_last_prices, safe_rerun, fetch_prices_for_ticker, normalize_prices
from risk_dashboard.ticker_utils import normalize_ticker, normalize_ticker_simple
from risk_dashboard.time_utils import _harmonize_index_tz, _make_index_naive
from risk_dashboard.price_utils import _pick_price_column, _extract_price_series_from_yf
from risk_dashboard.utils.parsers import safe_read_csv, safe_head_preview, DUMP_MARKERS

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

def handle_portfolio_upload_with_price_lookup(prefix: str = "profile", persist_path: Optional[Path] = None):
    """
    Upload handler for portfolio CSV.
    - persist_path: optional Path to save the raw uploaded file; if None default is data/holdings/portfolio.csv
    - reads CSV with safe_read_csv (filters dump markers),
    - normalizes columns, parses numerics, computes market_value if possible,
    - groups by ticker and stores cleaned df in st.session_state['portfolio_df'].
    """
    uploader_key = f"portfolio_uploader_{prefix}"
    uploaded = st.file_uploader("Portfolio CSV (ticker, quantity, price or market_value)", type=["csv"], key=uploader_key)
    if uploaded is None:
        return None

    try:
        # determine persist path
        if persist_path is None:
            persist_path = Path("data") / "holdings" / "portfolio.csv"
        # optional: use temp dir instead if you don't want persistent files
        # persist_path = Path(tempfile.gettempdir()) / f"portfolio_{prefix}.csv"

        persist_path.parent.mkdir(parents=True, exist_ok=True)
        # write raw bytes safely
        with open(persist_path, "wb") as f:
            f.write(uploaded.getbuffer())

        # --- robust read using markers from docs ---
        # safe_read_csv muss uploaded.seek(0) intern aufrufen
        df = safe_read_csv(uploaded, dump_markers=DUMP_MARKERS)

        # --- normalize column names first (so we can safely access columns) ---
        df.columns = [str(c).strip() for c in df.columns]
        colmap = {c.lower(): c for c in df.columns}

        if "ticker" not in colmap and "symbol" not in colmap:
            st.error("CSV benötigt Spalte 'ticker' oder 'symbol'.")
            return None

        # rename to canonical names
        df = df.rename(columns={
            colmap.get("ticker", ""): "ticker",
            colmap.get("symbol", ""): "ticker",
            colmap.get("quantity", ""): "quantity",
            colmap.get("shares", ""): "quantity",
            colmap.get("price", ""): "price",
            colmap.get("market_value", ""): "market_value"
        })

        # ensure ticker column exists and normalize tickers
        df["ticker"] = df["ticker"].astype(str).apply(normalize_ticker_simple)

        # parse numerics robustly (comma -> dot)
        df["quantity"] = pd.to_numeric(df.get("quantity", 0).astype(str).str.replace(",", "."), errors="coerce").fillna(0)
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "."), errors="coerce")
        if "market_value" in df.columns:
            df["market_value"] = pd.to_numeric(df["market_value"].astype(str).str.replace(",", "."), errors="coerce")

        # compute market_value if missing or NaN
        if "market_value" not in df.columns or df["market_value"].isna().any():
            if "price" in df.columns and not df["price"].isna().all():
                df["market_value"] = df["quantity"] * df["price"]
            else:
                # leave market_value as NaN for now; try to fill from prices_for_bt later
                df["market_value"] = df.get("market_value", pd.Series([pd.NA] * len(df)))

        # drop rows without ticker
        df = df.dropna(subset=["ticker"])
        # normalize tickers again (defensive)
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

        # group and aggregate AFTER numeric conversion and market_value computation
        agg_map = {"quantity": "sum", "market_value": "sum"}
        if "price" in df.columns:
            agg_map["price"] = lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA

        df_grouped = df.groupby("ticker", as_index=False).agg(agg_map)

        # ensure numeric market_value and quantity
        df_grouped["market_value"] = pd.to_numeric(df_grouped.get("market_value", 0), errors="coerce").fillna(0.0)
        df_grouped["quantity"] = pd.to_numeric(df_grouped.get("quantity", 0), errors="coerce").fillna(0)

        # persist cleaned df into session state
        st.session_state["portfolio_df"] = df_grouped
        st.session_state["portfolio_total_value"] = float(df_grouped["market_value"].sum())

        # debug output (safe)
        st.success(f"Portfolio geladen: {len(df_grouped)} Positionen, Gesamtwert {st.session_state['portfolio_total_value']:,.2f}")
        st.sidebar.write("DEBUG portfolio_df head", safe_head_preview(df_grouped, DUMP_MARKERS))
        st.sidebar.write("DEBUG portfolio_df dtypes", df_grouped.dtypes.to_dict())

        # attempt to fill missing market_value from prices_for_bt if any market_value == 0
        if (df_grouped["market_value"] == 0).any():
            try:
                prices = st.session_state.get("prices_for_bt", pd.DataFrame())
                if isinstance(prices, pd.DataFrame) and not prices.empty:
                    # build last price map (normalize price columns)
                    last_prices = {}
                    for col in prices.columns:
                        col_norm = normalize_ticker_simple(str(col))
                        last_series = prices[col].ffill().dropna()
                        if not last_series.empty:
                            last_prices[col_norm] = float(last_series.iloc[-1])
                    # apply mapping
                    def fill_mv(row):
                        mv = row.get("market_value")
                        if pd.notna(mv) and float(mv) > 0:
                            return float(mv)
                        t = normalize_ticker_simple(row["ticker"])
                        p = last_prices.get(t)
                        if p is not None:
                            return float(row["quantity"]) * float(p)
                        return float(mv) if pd.notna(mv) else 0.0
                    df_grouped["market_value"] = df_grouped.apply(fill_mv, axis=1)
                    # update totals and session
                    st.session_state["portfolio_df"] = df_grouped
                    st.session_state["portfolio_total_value"] = float(df_grouped["market_value"].sum())
            except Exception:
                logger.exception("Failed to fill market_value from prices_for_bt")

        # optionally trigger analysis handler if available
        try:
            from risk_dashboard.handlers import handle_holdings_analyse
            ok = handle_holdings_analyse()
            if ok:
                st.session_state["navigate_to"] = "Holdings Analyse"
                # safe rerun if you have such helper
                try:
                    from risk_dashboard.data_utils import safe_rerun
                    safe_rerun(stop=False)
                except Exception:
                    pass
        except Exception:
            logger.debug("handle_holdings_analyse not available or failed")

        return df_grouped

    except Exception as e:
        logger.exception("Fehler beim Upload/Verarbeiten: %s", e)
        st.error(f"Fehler beim Einlesen: {e}")
        return None

def add_new_tickers_to_portfolio(new_tickers: List[str], default_qty: int = 1):
    if not new_tickers:
        return
    # normalize and uppercase
    new_tickers_norm = [normalize_ticker(str(t)).upper() for t in new_tickers if t and str(t).strip()]
    if not new_tickers_norm:
        return
    pairs = [(t, default_qty) for t in new_tickers_norm]
    add_new_tickers_to_portfolio_with_quantities(pairs, default_qty=default_qty)

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
    if not pairs:
        return

    # Normalize input pairs (ticker -> normalized uppercase)
    norm_pairs = []
    for t, q in pairs:
        tn = normalize_ticker(str(t)).upper()
        try:
            qn = int(q) if q is not None else int(default_qty)
        except Exception:
            qn = int(default_qty)
        norm_pairs.append((tn, qn))

    # Load or init portfolio_df with correct columns and dtypes
    df = st.session_state.get("portfolio_df")
    if df is None or df.empty:
        df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])
    df = df.copy()

    # normalize existing tickers and ensure dtypes
    if "ticker" not in df.columns:
        df["ticker"] = ""
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if "quantity" not in df.columns:
        df["quantity"] = 0
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)

    # prepare price cache (DataFrame preferred)
    prices_cache = st.session_state.get("prices_for_bt")
    prices_df = prices_cache if isinstance(prices_cache, pd.DataFrame) and not prices_cache.empty else None

    # collect last_prices for missing tickers
    last_prices = {}
    need_fetch = []

    existing_set = set(df["ticker"].tolist())

    for t, q in norm_pairs:
        if t in existing_set:
            # add quantity to existing row
            df.loc[df["ticker"] == t, "quantity"] = df.loc[df["ticker"] == t, "quantity"].astype(int) + int(q)
            continue
        # try to find price in prices_df
        price_found = None
        if prices_df is not None:
            # direct column match (case-insensitive)
            for col in prices_df.columns:
                if normalize_ticker(str(col)).upper() == t:
                    try:
                        series = prices_df[col]
                        price_found = float(series.ffill().iloc[-1])
                        break
                    except Exception:
                        price_found = None
        if price_found is not None:
            last_prices[t] = price_found
        else:
            need_fetch.append(t)

    # fetch missing last prices (fallback)
    if need_fetch:
        fetched = fetch_last_prices(need_fetch, lookback_days=365)  # returns dict ticker->price
        for k, v in fetched.items():
            last_prices[normalize_ticker(k).upper()] = v

    # append new rows
    new_rows = []
    for t, q in norm_pairs:
        if t in existing_set:
            continue  # already added above
        price = last_prices.get(t)
        mv = float(q) * float(price) if price is not None else pd.NA
        new_rows.append({"ticker": t, "quantity": int(q), "price": price if price is not None else pd.NA,
                         "market_value": mv, "weight": pd.NA})

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    # consolidate and compute weights
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["market_value"] = pd.to_numeric(df.get("market_value", 0), errors="coerce").fillna(0.0)

    df = df.groupby("ticker", as_index=False).agg({
        "quantity": "sum",
        "price": lambda s: pd.to_numeric(s.dropna().astype(str).str.replace(",", "."), errors="coerce").iloc[0] if s.dropna().any() else pd.NA,
        "market_value": "sum",
        "weight": "first"
    })

    total_mv = float(df["market_value"].sum()) if not df.empty else 0.0
    if total_mv > 0:
        df["weight"] = (df["market_value"] / total_mv) * 100.0
    else:
        df["weight"] = 0.0

    # persist
    st.session_state["portfolio_df"] = df
    st.session_state["portfolio_total_value"] = total_mv

    # update price cache: prefer DataFrame; if not, merge last_prices into dict
    if isinstance(prices_df, pd.DataFrame) and not prices_df.empty:
        st.session_state["prices_for_bt"] = prices_df
    else:
        existing_cache = st.session_state.get("prices_for_bt", {})
        if isinstance(existing_cache, dict):
            existing_cache.update(last_prices)
            st.session_state["prices_for_bt"] = existing_cache
        else:
            st.session_state["prices_for_bt"] = last_prices

    st.success(f"{len(new_rows)} neue Ticker hinzugefügt, Gesamtwert {total_mv:,.2f}")
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

