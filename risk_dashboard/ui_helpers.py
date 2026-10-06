# risk_dashboard/ui_helpers.py
from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path
import streamlit as st
import logging


from risk_dashboard.data_utils import fetch_prices_from_yf, find_price_for_ticker, normalize_ticker, fetch_last_prices, safe_rerun
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

        uploaded.seek(0)
        df = pd.read_csv(uploaded)
        df.columns = [c.strip() for c in df.columns]
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

        df["quantity"] = pd.to_numeric(df.get("quantity"), errors="coerce")
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
        if "market_value" in df.columns:
            df["market_value"] = pd.to_numeric(df.get("market_value"), errors="coerce")

        if "market_value" not in df.columns or df["market_value"].isna().any():
            if "price" in df.columns and not df["price"].isna().all():
                df["market_value"] = df["quantity"] * df["price"]
            else:
                df = df.dropna(subset=["market_value"])
                if df.empty:
                    st.error("Keine gültigen Marktwerte vorhanden.")
                    return None

        df = df.dropna(subset=["ticker","quantity","market_value"])
        df = df.groupby("ticker", as_index=False).agg({"quantity":"sum","market_value":"sum"})
        total_mv = df["market_value"].sum()
        if total_mv == 0 or pd.isna(total_mv):
            st.error("Gesamtmarktwert ist 0 oder ungültig.")
            return None
        df["weight"] = df["market_value"] / total_mv

        # persist in session_state
        st.session_state["portfolio_df"] = df
        st.session_state["weights_by_ticker"] = dict(zip(df["ticker"], df["weight"]))
        st.session_state["portfolio_total_value"] = float(total_mv)

        st.success(f"Portfolio geladen: {len(df)} Positionen, Gesamtwert {total_mv:,.2f}")
        st.write(df)

        # setze navigate_to statt direkten Widget-Wert
        st.session_state["navigate_to"] = "Holdings Analyse"

        # versuche rerun nur wenn verfügbar, sonst zeige Hinweis/Button
        rerun_fn = getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            rerun_fn()
        else:
            st.info("Wechsel zur Analyse verfügbar. Klicke unten, um zur Analyse zu wechseln.")

            #if st.button("Zur Analyse wechseln", key="uihelpers_go_to_analysis"):
            #    st.session_state["app_sidebar_page_choice"] = "Holdings Analyse"
            #    safe_rerun()  # oder experimental_rerun, je nach Implementierung

            #if st.button("Zur Analyse wechseln"):
                # setze app_sidebar_page_choice direkt und force rerun if possible
            #    st.session_state["app_sidebar_page_choice"] = "Holdings Analyse"
            #    rerun_fn = getattr(st, "experimental_rerun", None)
            #    if callable(rerun_fn):
            #        rerun_fn()
            #    else:
            #        st.experimental_set_query_params(_nav="holdings")  # optionaler, harm. Fallback

        return df

    except Exception as e:
        logger.exception("Fehler beim Upload/Verarbeiten: %s", e)
        st.error(f"Fehler beim Einlesen: {e}")
        return None

def add_new_tickers_to_portfolio(new_tickers: List[str], default_qty: int = 1):
    """
    Fügt Ticker mit default_qty ins portfolio_df ein.
    new_tickers: List[str] (z. B. ["AAPL", "CSPX.L"])
    """
    if not new_tickers:
        return

    new_tickers_norm = [normalize_ticker(t) for t in new_tickers]

    df = st.session_state.get("portfolio_df")
    if df is None:
        df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # existing tickers (upper) verhindern doppelte Einträge
    existing = [str(x).upper() for x in df["ticker"].astype(str).tolist()]

    to_add = []
    for t in new_tickers_norm:
        if t.upper() in existing:
            continue
        to_add.append((t, default_qty))

    if to_add:
        # Reuse the with-quantities function to avoid code duplication
        add_new_tickers_to_portfolio_with_quantities(to_add, default_qty=default_qty)

def add_new_tickers_to_portfolio_with_quantities(pairs: List[Tuple[str,int]], default_qty: int = 1):
    """
    pairs: List of (ticker, qty)
    Fügt Ticker mit exakter Menge ins portfolio_df ein.
    Aktualisiert st.session_state['portfolio_df'] und st.session_state['prices_for_bt'].
    """
    if not pairs:
        return

    # Normalisiere Eingaben und baue qty_map
    qty_map = {normalize_ticker(str(t)): int(q) if q is not None else default_qty for t, q in pairs}

    # Lade oder initialisiere portfolio_df
    df = st.session_state.get("portfolio_df")
    if df is None:
        df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # Preiscache aus Session
    prices_cache = st.session_state.get("prices_for_bt")
    prices_df = prices_cache if isinstance(prices_cache, pd.DataFrame) else None

    # Sammle Ticker, die wir neu holen müssen
    need_fetch = []
    last_prices = {}

    existing_tickers_upper = [str(x).upper() for x in df["ticker"].astype(str).tolist()]

    for t_norm, qty in qty_map.items():
        # überspringe, wenn bereits in portfolio vorhanden
        if t_norm in existing_tickers_upper:
            continue
        # versuche Preis aus prices_df zu finden
        if prices_df is not None:
            series = find_price_for_ticker(prices_df, t_norm)
            if series is not None and not series.empty:
                try:
                    last_prices[t_norm] = float(series.ffill().iloc[-1])
                    continue
                except Exception:
                    pass
        need_fetch.append(t_norm)

    # Fallback: fetch_last_prices für fehlende Ticker
    if need_fetch:
        fetched = fetch_last_prices(need_fetch, lookback_days=365)
        for k, v in fetched.items():
            last_prices[normalize_ticker(k)] = v

    # Füge Zeilen hinzu
    for t_norm, qty in qty_map.items():
        if t_norm in existing_tickers_upper:
            # Optional: hier könntest du Menge addieren statt überspringen
            continue
        price = last_prices.get(t_norm)
        mv = float(qty) * float(price) if price is not None else 0.0
        row = {"ticker": t_norm, "quantity": int(qty), "price": price if price is not None else None,
               "market_value": mv, "weight": 0.0}
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    # Recompute weights
    total_mv = df["market_value"].sum() if not df.empty else 0.0
    if total_mv > 0:
        df["weight"] = (df["market_value"] / total_mv) * 100.0
    else:
        df["weight"] = 0.0

    # Update session
    st.session_state["portfolio_df"] = df
    st.session_state["portfolio_total_value"] = float(total_mv)

    # Update price cache: prefer DataFrame, sonst dict of last prices
    if isinstance(prices_df, pd.DataFrame) and not prices_df.empty:
        st.session_state["prices_for_bt"] = prices_df
    else:
        existing_cache = st.session_state.get("prices_for_bt", {})
        if isinstance(existing_cache, dict):
            existing_cache.update(last_prices)
            st.session_state["prices_for_bt"] = existing_cache
        else:
            st.session_state["prices_for_bt"] = last_prices

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

def add_tickers_and_fetch(tickers: list[str], prefix: str = "etf", start: str = None, end: str = None):
    success = []
    failed = []
    prices_accum = {}

    for t in tickers:
        t = t.strip()
        if not t:
            continue
        df = fetch_prices_for_ticker(t, start=start, end=end, auto_adjust=True, threads=False)
        if df is None or (hasattr(df, "empty") and df.empty):
            failed.append(t)
            logger.debug("add_tickers_and_fetch: no data for %s", t)
            continue

        df_norm = normalize_prices(df)
        if df_norm.empty:
            failed.append(t)
            continue

        # pick sensible column (prefer Close)
        if df_norm.shape[1] > 1:
            if "Close" in df_norm.columns:
                col = "Close"
            else:
                col = df_norm.columns[0]
            prices_accum[t] = df_norm[col]
        else:
            prices_accum[t] = df_norm.iloc[:, 0]

        success.append(t)

    combined = pd.DataFrame()
    if prices_accum:
        try:
            combined = pd.concat(prices_accum, axis=1)
            combined.columns = [str(c) for c in combined.columns]
        except Exception:
            combined = pd.DataFrame(prices_accum)

    if not combined.empty:
        st.session_state.setdefault("user_tickers", [])
        for t in success:
            if t not in st.session_state["user_tickers"]:
                st.session_state["user_tickers"].append(t)
        existing = st.session_state.get("prices_for_bt")
        if existing is None or (hasattr(existing, "empty") and existing.empty):
            st.session_state["prices_for_bt"] = combined
        else:
            try:
                merged = pd.concat([existing, combined], axis=1)
                merged = merged.loc[:, ~merged.columns.duplicated()]
                st.session_state["prices_for_bt"] = merged
            except Exception:
                st.session_state["prices_for_bt"] = combined

    return success, failed, combined
