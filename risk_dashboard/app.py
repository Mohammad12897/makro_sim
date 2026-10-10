# risk_dashboard/app.py
# $env:PYTHONPATH="C:\Projects\makro_sim"
# im aktivierten venv
# python -m pip install --upgrade pip
# python -m pip install plotly pandas yfinance streamlit
# python -m pip install numpy scikit-learn hmmlearn prophet
# pip install --upgrade yfinance==0.2.54
# pip install pre-commit
# pre-commit install
# pip install requests
# pip uninstall -y pandas-datareader pandas
# pip install pandas==2.1.3 pandas-datareader==0.10.0
# pip install yfinance pandas matplotlib plotly
# chcp 65001
# Öffne danach ein neues PowerShell-Fenster, damit die Variable geladen wird.
# .\.venv\Scripts\Activate.ps1
# $env:AUTO_FIX_PASTE_BLOCKS="true"
# python -m streamlit run .\risk_dashboard\app.py
# python -m streamlit run .\risk_dashboard\app.py --logger.level=debug > .\streamlit_full.log 2>&1
# python -m streamlit run .\risk_dashboard\app.py --server.runOnSave=false

# risk_dashboard/app.py
# --- Logging must be configured before importing streamlit or other app modules ---
import os
import re
import sys
import logging
import threading
from pathlib import Path


# Project root and output dirs
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
out_dir = project_root / "data" / "backtests"
out_dir.mkdir(parents=True, exist_ok=True)

# Logging: zentrale Konfiguration aktivieren (einmalig)
from risk_dashboard.logging_config import configure_logging

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app_exceptions.log")

# configure_logging muss VOR allen logger-Aufrufen stehen
configure_logging(log_level=logging.DEBUG, logfile=log_file, run_id="-")

# Optional: root logger Referenz
root_logger = logging.getLogger()

# Uncaught exceptions -> log via logger (verwende den zentral konfigurierten Logger)
def _log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger(__name__).exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = _log_unhandled_exception

def _thread_excepthook(args):
    logging.getLogger(__name__).exception("Uncaught thread exception", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

threading.excepthook = _thread_excepthook

# Testlog (kein direkter File‑Write nötig)
logging.getLogger(__name__).info("LOGGING INITIALIZED")


# --- Now import streamlit and the rest of your app modules ---
import locale
import logging as _logging  # keep alias if needed
import streamlit as st
# other imports follow...
from typing import Optional, Any, Dict

import numpy as np
import plotly.graph_objects as go
from risk_dashboard.data_utils import do_add_tickers, is_prices_empty, normalize_prices, safe_rerun, fetch_prices_quiet_with_used, sanitize_session_state
from risk_dashboard.ui.profiles_ui import show_holdings_uploader
print(">>> APP STARTED: TOP OF app.py", flush=True)


def add_ticker_callback(prefix, asset_key, stable_input_key):
    if st.session_state.get("_processing_add", False):
        return
    st.session_state["_processing_add"] = True
    try:
        raw_val = (st.session_state.get(stable_input_key, "") or "").strip()
        prices = st.session_state.get("prices_for_bt")
        if raw_val:
            mapped, missing = do_add_tickers([raw_val], prefix, asset_key, prices=prices)
            st.session_state[stable_input_key] = ""

            # Debug: was wurde gemappt / fehlt
            logger.debug("add_ticker_callback mapped=%s missing=%s raw=%s", mapped, missing, raw_val)
            st.sidebar.write("DEBUG add_ticker_callback mapped", mapped)
            st.sidebar.write("DEBUG add_ticker_callback missing", missing)
            # optional: show current prices_for_bt cols
            prices = st.session_state.get("prices_for_bt")
            st.sidebar.write("DEBUG prices_for_bt cols", None if prices is None else list(prices.columns))
            # Feedback
            if missing:
                st.warning(f"Automatisches Mapping fehlgeschlagen für: {missing}")
    finally:
        st.session_state["_processing_add"] = False
        safe_rerun(stop=False)


# UTF-8 erzwingen (sicher)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
except Exception:
    pass

logger = logging.getLogger(__name__)
# Safety check before any heavy imports (optional)
AUTO_FIX = os.getenv("AUTO_FIX_PASTE_BLOCKS", "false").lower() in ("1", "true", "yes")

from risk_dashboard.config import DEFAULT_START_STR, UNIVERSE_PATHS

# Import minimal safety module if vorhanden
try:
    from risk_dashboard.core.safety import DUMP_MARKERS
except Exception as e:
    logger.warning("Could not import safety markers: %s. Continuing without safety markers.", e)
    DUMP_MARKERS = []

sanitize_session_state ()

# initialisierung vor allen Widgets
for prefix in ("etf", "stock", "mixed"):
    asset_key = f"{prefix}_asset_type"
    stable_input_key = f"{prefix}_ticker_input"
    if asset_key not in st.session_state:
        st.session_state[asset_key] = "ETF"
    if stable_input_key not in st.session_state:
        st.session_state[stable_input_key] = ""
# danach rufe render_etf_selection_ui(prefix="etf") etc.


# Optional: implementiere startup_safety_check in safety.py oder hier eine leichte Variante
def _default_startup_safety_check(root, markers, auto_fix=False):
    # einfache Prüfung: suche Marker in repo; nur Warnungen, keine harte Fehler
    import subprocess, shlex, sys
    try:
        if not markers:
            logger.debug("No dump markers provided; skipping safety grep.")
            return
        pattern = "|".join([m.replace('"', '\\"') for m in markers])
        cmd = f"git grep -n -E \"{pattern}\" -- ':!vendor' ':!node_modules' || true"
        proc = subprocess.run(cmd, shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = proc.stdout.strip()
        if out:
            logger.warning("Potential dump markers found in repo:\n%s", out)
            if auto_fix:
                logger.info("AUTO_FIX requested but automatic fixes are not implemented here.")
    except Exception:
        logger.exception("startup safety check failed")

# Call the check (you can replace with a more advanced startup_safety_check if you have one)
try:
    _default_startup_safety_check(project_root, DUMP_MARKERS, auto_fix=AUTO_FIX)
except Exception:
    logger.exception("Safety check raised an exception; continuing.")


# Eigene Module (lokale Projektstruktur)
from risk_dashboard.core.data_loader import (
    load_raw_prices_for_universe,
    load_price_data,
    filter_valid_tickers
)
from risk_dashboard.core.ticker_cache import validate_ticker_with_cache
from risk_dashboard.data_cache import load_price_data_cached

# Streamlit optional importieren, mit sauberem Shim als Fallback
import os
import pandas as pd
import plotly.express as px


# initialisiere Flag falls nötig
if "backtest_ran" not in st.session_state:
    st.session_state["backtest_ran"] = False


try:
    import plotly.express as px
except Exception:  # pragma: no cover - provide minimal px fallback
    def _line(series, title=None):
        fig = go.Figure()
        try:
            fig.add_trace(go.Scatter(y=series.values, mode='lines', name=title))
        except Exception:
            pass
        if title:
            fig.update_layout(title=title)
        return fig
    def _area(series, title=None):
        fig = go.Figure()
        try:
            fig.add_trace(go.Scatter(y=series.values, fill='tozeroy', mode='none', name=title))
        except Exception:
            pass
        if title:
            fig.update_layout(title=title)
        return fig
    class _PXShim:
        line = staticmethod(_line)
        area = staticmethod(_area)
    px = _PXShim()
# Core functions (können fehlen, daher try/except)
try:
    from risk_dashboard.core.analysis import compute_metrics, analyze_ticker
except Exception:
    # fallback compute_metrics if missing
    def compute_metrics(close_series: pd.Series, trading_days: int = 252, rf: float = 0.0) -> dict:
        close_series = pd.to_numeric(close_series, errors="coerce").dropna()
        if close_series.empty:
            raise ValueError("Close-Serie ist leer oder enthält keine numerischen Werte")
        rets = close_series.pct_change().dropna()
        ann_ret = (1 + rets.mean()) ** trading_days - 1
        ann_vol = rets.std() * (trading_days ** 0.5)
        sharpe = (ann_ret - rf) / ann_vol if ann_vol != 0 else float("nan")
        cum = (1 + rets).cumprod()
        peak = cum.cummax()
        drawdown = (cum - peak) / peak
        max_dd = drawdown.min()
        return {
            "annual_return": float(ann_ret),
            "annual_vol": float(ann_vol),
            "sharpe": float(sharpe),
            "max_drawdown": float(max_dd)
        }

print(">>> AFTER BIG IMPORTS", flush=True)


def analyze_single_etf(ticker: str):
    st.write(f"Analyse für **{ticker}**")

    # 1. Preise laden (mit Spinner)
    with st.spinner("Preise laden und Kennzahlen berechnen..."):
        df = load_price_data_cached(ticker)  # akzeptiert String oder Liste
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.error("Keine Preisdaten verfügbar für " + ticker)
        return

    # 2. close Serie extrahieren und prüfen (robust gegenüber 'Close' / 'close' / MultiIndex)
    close = None
    # Falls MultiIndex-Spalten, versuche 'Close' Ebene oder letzte Ebene
    if isinstance(df.columns, pd.MultiIndex):
        # Versuche Ebene 'Close' zuerst
        if "Close" in df.columns.get_level_values(0):
            try:
                close = df.xs("Close", axis=1, level=0, drop_level=False).iloc[:, 0].dropna()
            except Exception:
                pass
        if close is None:
            # Fallback: nimm erste Spalte der letzten Ebene
            try:
                df.columns = df.columns.get_level_values(-1)
            except Exception:
                pass

    # Nicht-MultiIndex oder Fallback
    if close is None:
        if "Close" in df.columns:
            close = df["Close"].dropna()
        elif "close" in df.columns:
            close = df["close"].dropna()
        else:
            # Fallback: erste numerische Spalte
            numeric_cols = df.select_dtypes("number").columns.tolist()
            if numeric_cols:
                close = df[numeric_cols[0]].dropna()

    if close is None or close.empty:
        st.error("Keine verwertbare Close‑Serie für " + ticker)
        return

    # 3. Kennzahlen berechnen
    try:
        metrics = compute_metrics(close)
        st.write(metrics)
    except Exception as e:
        st.error(f"Fehler bei der Berechnung der Kennzahlen: {e}")
        return

    # 4. Darstellung (Metrics + Plots) ...
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAGR", f"{metrics['annual_return']*100:.2f} %")
    c2.metric("Volatilität", f"{metrics['annual_vol']*100:.2f} %")
    c3.metric("Sharpe", f"{metrics['sharpe']:.2f}")
    c4.metric("Max Drawdown", f"{metrics['max_drawdown']*100:.2f} %")

    fig = px.line(close, title=f"Preisverlauf von {ticker}")
    #st.plotly_chart(fig, use_container_width=True)
    st.plotly_chart(fig, width="stretch")

    rets = close.pct_change().dropna()
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    fig_dd = px.area(dd, title=f"Drawdown von {ticker}")
    st.plotly_chart(fig_dd, use_container_width=True)

def analyze_single_etf_using_df(ticker: str, price_df: pd.DataFrame):
    st.write(f"Analyse für **{ticker}**")

    # Versuche, die passende Close‑Serie aus price_df zu extrahieren (robust)
    close = pd.Series(dtype=float)

    # 1) Wenn DataFrame MultiIndex columns (yfinance multi-ticker)
    if isinstance(price_df.columns, pd.MultiIndex):
        # Suche tolerant nach Close/Adj Close Varianten
        for field in ("Close", "close", "Adj Close", "AdjClose"):
            if (ticker, field) in price_df.columns:
                close = pd.to_numeric(price_df[(ticker, field)], errors="coerce").dropna()
                break

    # 2) Wenn single-level columns and ticker is a column
    if close.empty and ticker in price_df.columns:
        close = pd.to_numeric(price_df[ticker], errors="coerce").dropna()

    # 3) Wenn eine 'close' Spalte existiert (z. B. project_fetch liefert {'close': Series})
    if close.empty and "close" in price_df.columns:
        # handle both Series and DataFrame cases
        col = price_df["close"]
        if isinstance(col, pd.Series):
            close = pd.to_numeric(col, errors="coerce").dropna()
        else:
            # DataFrame: wähle Spalte mit ticker oder erste numerische Spalte
            if ticker in col.columns:
                close = pd.to_numeric(col[ticker], errors="coerce").dropna()
            else:
                # fallback to first numeric column
                numeric_cols = col.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    close = pd.to_numeric(col[numeric_cols[0]], errors="coerce").dropna()

    # 4) Letzter Fallback: erste numerische Spalte der gesamten DF
    if close.empty:
        numeric_cols = price_df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            close = pd.to_numeric(price_df[numeric_cols[0]], errors="coerce").dropna()

    if close is None or close.empty:
        st.error("Keine Close‑Daten für " + ticker)
        return

    # Kennzahlen berechnen
    try:
        metrics = compute_metrics(close)
    except Exception as e:
        st.error(f"Fehler bei der Berechnung der Kennzahlen: {e}")
        return

    # Darstellung (Metrics + Plots)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAGR", f"{metrics['annual_return']*100:.2f} %")
    c2.metric("Volatilität", f"{metrics['annual_vol']*100:.2f} %")
    c3.metric("Sharpe", f"{metrics['sharpe']:.2f}")
    c4.metric("Max Drawdown", f"{metrics['max_drawdown']*100:.2f} %")

    fig = px.line(close, title=f"Preisverlauf von {ticker}")
    #st.plotly_chart(fig, use_container_width=True)
    st.plotly_chart(fig, width="stretch")

    rets = close.pct_change().dropna()
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    fig_dd = px.area(dd, title=f"Drawdown von {ticker}")
    st.plotly_chart(fig_dd, use_container_width=True)


# --- Imports oben in app.py ---

# --- Docs / dynamische Seitenliste ---
from risk_dashboard.ui_helpers import (
    handle_portfolio_upload_with_price_lookup,
    load_markdown_safe,
    show_intro,
    status_legend,
    consolidate_portfolio_df,
)
from risk_dashboard.data_utils import fetch_prices_from_yf, normalize_ticker

# Page config ganz oben
st.set_page_config(page_title="Risk Dashboard", layout="wide")
st.sidebar.title("Navigation")

# Docs automatisch
docs_dir = project_root / "risk_dashboard" / "docs"
docs = sorted(docs_dir.glob("*.md"))
pages_from_docs = {p.stem: str(p) for p in docs}
custom_pages = {"Dashboard": None, "Upload": None, "Holdings Analyse": None}
pages = dict(pages_from_docs)
for k in custom_pages:
    if k not in pages:
        pages[k] = None

page_options = list(pages.keys())

# If a previous safe_rerun set this flag, process navigation defaults now
if st.session_state.pop("_needs_rerun", False):
    default_choice = st.session_state.pop("navigate_to", None)
    if default_choice:
        st.session_state.setdefault("app_sidebar_page_choice", default_choice)

# Sidebar-Selectbox (einmalig)
choice = st.sidebar.selectbox("Seite wählen", options=page_options, key="app_sidebar_page_choice")

# kontextuelle Einführung nur wenn md vorhanden
md_path = pages.get(choice)
if isinstance(md_path, str) and md_path.endswith(".md"):
    show_intro(md_path)

st.title("Macroeconomic Risk Dashboard")

# per-render registry (muss VOR uploader/widget-Aufrufen stehen)
ss = st.session_state
ss["_rendered_widget_keys"] = []


# --- Seiteninhalt ---
if choice == "Dashboard":
    st.header("Übersicht")
    status_legend()
    st.write("Hier kommen Charts, KPIs, etc.")

elif choice == "Backtest Rezept":
    st.header("Backtest Rezept")
    md_full = load_markdown_safe(pages.get("backtest-recipe", "risk_dashboard/docs/backtest-recipe.md"))
    if md_full:
        st.markdown(md_full, unsafe_allow_html=False)
    else:
        st.warning("Backtest‑Dokument nicht gefunden. Die Analyse ist trotzdem verfügbar.")
    # ... ETF Vergleich Block ...

# Upload Tab
elif choice == "Upload":
    st.header("Portfolio Upload")
    st.markdown("**Portfolio-CSV (Ticker, Menge, Preis, market_value optional)**")

    # Upload-Handler (schreibt file + session_state["portfolio_df"])
    handle_portfolio_upload_with_price_lookup(prefix="profile")

    # Sidebar/Handler Ticker-Synchronisation (sofort nach Hinzufügen)
    # 1) Session-Daten / Fallback-Synchronisation
    user_tickers = st.session_state.get("user_tickers", [])

    # prefer explicit portfolio_df, but fallback to portfolio (compatibility)
    df = st.session_state.get("portfolio_df")
    if df is None:
        # try legacy key
        legacy = st.session_state.get("portfolio")
        if legacy is not None:
            # normalize legacy to portfolio_df shape
            df = legacy.copy()
            # ensure required columns exist
            for col in ("price", "market_value", "weight"):
                if col not in df.columns:
                    df[col] = None
            df = df[["ticker", "quantity", "price", "market_value", "weight"]]
        else:
            df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # Konsolidieren, falls nötig (bereinigt Rohstrings wie "DAX 3")
    try:
        from risk_dashboard.ui_helpers import consolidate_portfolio_df
        if df is not None and not df.empty:
            df = consolidate_portfolio_df(df)
            st.session_state["portfolio_df"] = df
    except Exception as e:
        # Loggen, aber nicht abbrechen
        logger.exception("Fehler bei consolidate_portfolio_df im Upload-Block: %s", e)

    # Nur neue, noch nicht vorhandene Ticker ermitteln (normalisiert, Uppercase)
    existing = [str(x).upper() for x in df["ticker"].astype(str).tolist()] if not df.empty else []
    new_tickers = [t for t in user_tickers if t and t.upper() not in existing]

    if new_tickers:
        from risk_dashboard.ui_helpers import add_new_tickers_to_portfolio

        # Portfolio aktualisieren (kein Fetch hier)
        add_new_tickers_to_portfolio(new_tickers)

        # nach Einlesen und Aggregation
        df = df.groupby("ticker", as_index=False).agg({"quantity":"sum","market_value":"sum"})
        total_mv = df["market_value"].sum()
        if total_mv == 0 or pd.isna(total_mv):
            st.error("Gesamtmarktwert ist 0 oder ungültig.")
            return None

        # persist
        st.session_state["portfolio_df"] = df
        st.session_state["weights_by_ticker"] = dict(zip(df["ticker"], df["weight"]))
        st.session_state["portfolio_total_value"] = float(total_mv)

        # prices_for_bt defensiv setzen
        st.session_state["prices_for_bt"] = combined if (combined is not None and not combined.empty) else pd.DataFrame()


        # sichere Navigation: setze Flag und rerun einmal
        st.session_state["navigate_to"] = "Holdings Analyse"
        safe_rerun(stop=False)


    # Button: manuelle Navigation zur Analyse
    if st.button("Zur Analyse wechseln", key="app_go_to_analysis"):
        st.session_state["navigate_to"] = "Holdings Analyse"
        safe_rerun(stop=False)

    # Debug-Ausgaben (nur kurz, keine großen Dumps)
    st.sidebar.write("portfolio_df head:", st.session_state.get("portfolio_df"))
    prices_for_bt = st.session_state.get("prices_for_bt")
    st.sidebar.write("prices_for_bt cols:", list(prices_for_bt.columns) if isinstance(prices_for_bt, pd.DataFrame) else prices_for_bt)


# Holdings Analyse
elif choice == "Holdings Analyse":
    st.header("Holdings Analyse")
    status_legend()

    # 1) Session-Daten / Fallback-Synchronisation
    user_tickers = st.session_state.get("user_tickers", [])

    # prefer explicit portfolio_df, but fallback to portfolio (compatibility)
    df = st.session_state.get("portfolio_df")
    if df is None:
        # try legacy key
        legacy = st.session_state.get("portfolio")
        if legacy is not None:
            # normalize legacy to portfolio_df shape
            df = legacy.copy()
            # ensure required columns exist
            for col in ("price", "market_value", "weight"):
                if col not in df.columns:
                    df[col] = None
            df = df[["ticker", "quantity", "price", "market_value", "weight"]]
        else:
            df = pd.DataFrame(columns=["ticker", "quantity", "price", "market_value", "weight"])

    # Normalisiere vorhandene ticker-Liste
    existing = [str(x).upper() for x in df["ticker"].astype(str).tolist()] if not df.empty else []

    # Neue Ticker automatisch mit Preisen hinzufügen (nur wenn noch nicht vorhanden)
    new_tickers = [t for t in user_tickers if t and t.upper() not in existing]
    if new_tickers:
        from risk_dashboard.ui_helpers import add_new_tickers_to_portfolio
        add_new_tickers_to_portfolio(new_tickers)

    # lade aktualisiertes df aus session (falls add_new... es aktualisiert hat)
    df = st.session_state.get("portfolio_df", df)

    # --- Sicherer prices-Guard
    prices = st.session_state.get("prices_for_bt")
    if prices is None:
        prices = pd.DataFrame()
    logger.debug("Holdings Analyse: portfolio_df present=%s", "portfolio_df" in st.session_state)
    st.sidebar.write("DEBUG portfolio_df", st.session_state.get("portfolio_df"))
    st.sidebar.write("DEBUG prices_for_bt cols", None if prices is None else list(prices.columns))

    # Konsolidieren und Normalisieren
    from risk_dashboard.ui_helpers import consolidate_portfolio_df
    df = consolidate_portfolio_df(df)
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0).astype(int)
    df["price"] = pd.to_numeric(df.get("price"), errors="coerce")  # CSV-Preise numerisch

    # Wenn keine Preisdaten vorhanden sind: Warnung, aber nicht die ganze App crashen
    if prices is None or getattr(prices, "empty", True):
        st.warning("Preisdaten sind nicht geladen. Bitte Preise laden oder Cache prüfen.")
        st.subheader("Holdings Tabelle")
        st.dataframe(df.reset_index(drop=True))
        st.stop()

    # Mapping holdings -> price columns (case-insensitive)
    cols_upper_map = {c.upper(): c for c in prices.columns}
    mapped_cols = []
    missing = []
    for t in df["ticker"].astype(str).str.upper().str.strip():
        if t in cols_upper_map:
            mapped_cols.append(cols_upper_map[t])
        else:
            t_simple = re.sub(r'(\.L$|-USD$|/USD$)', '', t)
            candidate = None
            for cu, orig in cols_upper_map.items():
                if cu == t_simple or cu.startswith(t_simple) or t_simple.startswith(cu):
                    candidate = orig
                    break
            if candidate:
                mapped_cols.append(candidate)
            else:
                mapped_cols.append(None)
                missing.append(t)

    if missing:
        st.warning(f"Für diese Ticker fehlen Preise oder Mapping: {', '.join(missing)}")
        logger.debug("Holdings Analyse missing mapping: %s", missing)

    available_mapped = [c for c in mapped_cols if c is not None]
    if not available_mapped:
        st.info("Keine passenden Preisspalten für Performance‑Berechnung gefunden.")
        st.subheader("Holdings Tabelle")
        st.dataframe(df.reset_index(drop=True))
        st.stop()

    # letzte Preise extrahieren
    last_prices = {}
    for col in available_mapped:
        s = prices[col].dropna()
        if not s.empty:
            last_prices[col.upper()] = s.iloc[-1]

    # Build map_df and merge (left join preserves CSV price)
    map_df = pd.DataFrame({
        "ticker_norm": df["ticker"].astype(str).str.upper().str.strip(),
        "mapped_col": mapped_cols
    })
    display = df.copy()
    display["ticker_norm"] = display["ticker"].astype(str).str.upper().str.strip()
    display = display.merge(map_df, on="ticker_norm", how="left")

    # Normalize last_prices keys and choose price: prefer CSV price, fallback to last_prices
    last_prices_upper = {k.upper(): v for k, v in last_prices.items()}

    def choose_price(row):
        p = row.get("price")
        if pd.notna(p) and p != 0:
            return p
        mc = row.get("mapped_col")
        if mc:
            return last_prices_upper.get(mc.upper())
        return None

    display["price"] = display.apply(choose_price, axis=1)

    # compute market_value and weight
    display["market_value"] = display["quantity"] * display["price"].fillna(0)
    total_mv = display["market_value"].sum()
    display["weight"] = (display["market_value"] / total_mv * 100).fillna(0) if total_mv > 0 else 0

    # Anzeige (einmalig)
    st.subheader("Holdings Tabelle")
    st.dataframe(display[["ticker","quantity","price","market_value","weight"]].reset_index(drop=True))

    # Performance: nutze available_mapped (Original-Spaltennamen)
    available_for_perf = [c for c in available_mapped if c in prices.columns]
    if not available_for_perf:
        st.info("Keine passenden Preisspalten für Performance‑Berechnung gefunden.")
        st.stop()

    # Gewichtsdiagramm (robust) — aus display
    try:
        if "weight" in display.columns and not display["weight"].isnull().all() and (display["weight"] > 0).any():
            st.bar_chart(display.set_index("ticker")["weight"])
        else:
            st.write("Gewichtsdiagramm: keine gültigen 'weight' Werte vorhanden.")
    except Exception:
        st.write("Gewichtsdiagramm konnte nicht gezeichnet werden (prüfe 'weight' Spalte).")

    # 5) Performance (nur wenn Preisdaten vorhanden)
    if prices is not None and hasattr(prices, "columns") and len(prices.columns) > 0:
        st.subheader("Performance")

        # Tickerliste aus df (normalisiert) und Abgleich mit prices.columns
        tickers = df["ticker"].astype(str).tolist()
        # Falls nötig, normalisiere Groß-/Kleinschreibung: prices.columns sind oft exakt so wie in data
        available = [t for t in tickers if t in prices.columns]
        missing = [t for t in tickers if t not in prices.columns]
        if missing:
            st.warning(f"Für diese Ticker fehlen Preise: {', '.join(missing)} (werden ignoriert)")

        if available:
            # Gewichte als Bruchteile verwenden
            weights_pct = df.set_index("ticker")["weight"].reindex(available).fillna(0)
            weights = weights_pct / 100.0

            # Tagesrenditen
            returns = prices[available].pct_change().dropna(how="all")
            if returns.empty:
                st.info("Preisreihen vorhanden, aber keine Renditedaten (zu kurze Zeitreihe).")
            else:
                # Portfolio‑Rendite: returns * weights (weights als Spaltenvektor)
                port_ret = (returns * weights.values).sum(axis=1)

                # Kumulierte Equity (Start bei 1)
                cum = (1 + port_ret).cumprod()
                st.line_chart(cum.rename("Portfolio Equity"))

                # Kennzahlen
                ann_factor = 252
                total_return = cum.iloc[-1] - 1
                # Tage als Differenz der Datumsindizes (falls DatetimeIndex)
                try:
                    days = (cum.index[-1] - cum.index[0]).days
                except Exception:
                    days = len(cum)
                cagr = (cum.iloc[-1]) ** (365.0 / max(days, 1)) - 1
                vol = port_ret.std() * (ann_factor ** 0.5)
                sharpe = (port_ret.mean() * ann_factor) / (vol if vol > 0 else 1)
                running_max = cum.cummax()
                max_dd = ((cum / running_max) - 1).min()

                cols = st.columns(4)
                cols[0].metric("Total Return", f"{total_return:.2%}")
                cols[1].metric("CAGR", f"{cagr:.2%}")
                cols[2].metric("Volatilität (ann.)", f"{vol:.2%}")
                cols[3].metric("Sharpe (ann.)", f"{sharpe:.2f}")
                st.write(f"Max Drawdown: {max_dd:.2%}")

                st.subheader("Top Holdings")
                st.table(df.sort_values("weight", ascending=False).head(10).reset_index(drop=True))
        else:
            st.info("Keine passenden Preisreihen für die geladenen Ticker gefunden.")
    else:
        st.info("Keine Preisdaten vorhanden. Lade Preise oder aktiviere Preislookup im Upload.")

    # 6) Weitere Kennzahlen
    st.subheader("Weitere Kennzahlen")
    st.write("Gesamtwert:", f"{st.session_state.get('portfolio_total_value', 0):,.2f}")
    st.write("Anzahl Positionen:", df.shape[0])

    st.sidebar.write(fetch_prices_from_yf([normalize_ticker("NVDA")]).tail(3))

else:
    # Falls choice ein Markdown‑Dokument ist (aus docs), zeige es
    md_path = pages.get(choice)
    if isinstance(md_path, str) and md_path.endswith(".md"):
        md_full = load_markdown_safe(md_path)
        if md_full:
            st.markdown(md_full, unsafe_allow_html=False)
        else:
            st.info("Dokument nicht gefunden.")

# Weitere Core-Module (Risk, Scenario, FX, Market, Investment)
from risk_dashboard.core.risk_engine import (
    compute_pca_details,
    compute_risk_score_v2,
    detect_risk_regimes_from_scenario,
    build_scenario_series,
    build_fx_risk_factors,
    build_market_risk_factors,
)
from risk_dashboard.core.utils import (
    get_latest_before,
    ensure_date_column,
    normalize_price_df,
    ensure_date_series,
    analyze_portfolio_components,
    validate_prophet_input,
)
from risk_dashboard.core.macro_loader import load_and_validate_macro_data, load_macro_series
from risk_dashboard.core.scenario_engine import (
    load_base_data,
    apply_shock,
    SCENARIOS,
    build_baseline_scenario,
    build_scenario,
)
from risk_dashboard.core.fx_forecast import forecast_fx_arima, forecast_fx_prophet
from risk_dashboard.core.fx_engine import download_fx_history
from risk_dashboard.core.market_engine import download_etf_history
from risk_dashboard.core.glossary import GLOSSARY, get_definition, search_glossary
from risk_dashboard.core.investment_engine import (
    investment_recommendations_v3,
    regime_based_strategy,
    etf_screening_by_regime,
    backtest_etf_regime_portfolio,
    backtest_regime_risk_parity,
    backtest_regime_hrp,
    performance_stats,
    regime_heatmap_data,
    sharpe_per_regime,
    regime_transition_matrix,
    backtest_regime_strategy,
    generate_investment_package,
    map_regime_to_label,
    build_regime_risk_parity_portfolio,
)
from risk_dashboard.core.regime_model import (
    classify_regime_from_score,
    build_regime_timeline,
    compute_regime_transition_matrix,
    next_regime_distribution,
)
from risk_dashboard.core.etl import load_etf_universe_prices
from risk_dashboard.core.asset_packages import parse_etf_input
from risk_dashboard.ui.profiles_ui import is_nonempty, profile_form_ui, render_etf_tab
from risk_dashboard.core.weights import compute_abs_weights
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.regime_hmm import fit_hmm_regimes, map_hmm_states_to_labels
from risk_dashboard.core.config import load_profiles, save_profile, load_etf_universe

print(">>> AFTER BACKTESTS", flush=True)


# ---------------------------
# Helper functions (Top-level so they are available everywhere)
# ---------------------------
def _safe_row_get(row: Any, *keys: str, default: Any = None) -> Any:
    if row is None:
        return default
    for k in keys:
        try:
            if isinstance(row, dict) and k in row:
                return row[k]
            if hasattr(row, "get") and row.get(k, None) is not None:
                return row.get(k)
            if k in getattr(row, "index", []):
                return row[k]
        except Exception:
            continue
    return default

def get_investment_package(
    risk_score_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    regime_df: pd.DataFrame,
    generate_investment_package_fn
) -> Dict[str, Any]:
    """
    Liefert das aktuelle Investment-Paket als dict:
    {date, risk_score, scenario, regime, package}
    Erwartet: generate_investment_package_fn(regime, scenario, risk_score) -> dict
    """
    # robustes current_date aus risk_score_df
    if "date" in risk_score_df.columns:
        current_date = pd.to_datetime(risk_score_df["date"].iloc[-1])
    elif isinstance(risk_score_df.index, pd.DatetimeIndex):
        current_date = pd.to_datetime(risk_score_df.index[-1])
    else:
        raise RuntimeError("risk_score_df enthält keine 'date' Spalte und keinen DatetimeIndex.")

    # --- risk row ---
    tmp = get_latest_before(risk_score_df, "date", current_date)
    if tmp is None:
        tmp = get_latest_before(risk_score_df, None, current_date)
    current_risk_row = tmp

    # --- scenario row ---
    tmp = get_latest_before(scenario_df, "date", current_date)
    if tmp is None:
        tmp = get_latest_before(scenario_df, None, current_date)
    current_scenario_row = tmp

    # --- regime row ---
    tmp = get_latest_before(regime_df, "date", current_date)
    if tmp is None:
        tmp = get_latest_before(regime_df, None, current_date)
    current_regime_row = tmp

    # risk_score extrahieren (Versuche mehrere Keys, dann NaN)
    _risk_val = _safe_row_get(current_risk_row, "risk_score", "risk_score_pca", default=float("nan"))
    try:
        risk_score = float(_risk_val)
    except Exception:
        risk_score = float("nan")

    scenario = _safe_row_get(current_scenario_row, "scenario", "label", default=None)
    regime = _safe_row_get(current_regime_row, "regime", "label", default=None)

    package = {}
    try:
        package = generate_investment_package_fn(regime, scenario, risk_score)
    except Exception:
        logging.getLogger(__name__).exception("generate_investment_package_fn schlug fehl")
        package = {}

    return {
        "date": current_date,
        "risk_score": risk_score,
        "scenario": scenario,
        "regime": regime,
        "package": package
    }

# ---------------------------
# Streamlit page config and session defaults
# ---------------------------
st.set_page_config(page_title="Macro Risk Dashboard", layout="wide")

if "show_lexikon" not in st.session_state:
    st.session_state.show_lexikon = False

if "low_risk_selected" not in st.session_state:
    st.session_state["low_risk_selected"] = ["CSPX.L", "EUNL.DE"]
if "med_risk_selected" not in st.session_state:
    st.session_state["med_risk_selected"] = ["IMEU.L", "IQQ0.DE"]
if "high_risk_selected" not in st.session_state:
    st.session_state["high_risk_selected"] = ["AGGG.L", "SGLN.L"]

AVAILABLE_ETF = [
    "CSPX.L","EQQQ.L","EUNL.DE","IQQ0.DE","IMEU.L",
    "AGGG.L","IEGA.L","SGLN.L","PCOM.L"
]

# Kopierfertig: aktualisierte Sidebar-Funktion
def render_sidebar(available_etfs):
    # Lokale Importe (anpassen, falls Pfade anders sind)
    from risk_dashboard.ui_helpers import add_new_tickers_to_portfolio_with_quantities
    from risk_dashboard.input_parsing import parse_ticker_input

    # Optional: falls analyze_ticker in einem Modul liegt
    try:
        from risk_dashboard.core.analysis import analyze_ticker
    except Exception:
        analyze_ticker = None

    st.sidebar.title("Portfolio Eingabe")

    # ----- Bulk / Freitext Eingabe (unterstützt TICKER, TICKER:QTY, mehrere Einträge) -----
    # Sidebar: Schnell hinzufügen
    st.sidebar.subheader("Schnell hinzufügen")
    prefix = "main"  # passe an, falls du mehrere Bereiche hast
    logger.debug("st.sidebar.text_area with prefix=%s", prefix)

    ticker_raw = st.sidebar.text_area(
        "Ticker hinzufügen (z. B. NVDA oder DAX:1, BTC 2)",
        placeholder="z. B. NVDA oder DAX:1, BTC 2",
        key=f"{prefix}_sidebar_ticker_raw",
        height=100,
    )

    qty_default = st.sidebar.number_input(
        "Menge (Default für Einträge ohne Menge)",
        min_value=0,
        value=1,
        step=1,
        key=f"{prefix}_sidebar_qty_default",
    )

    from risk_dashboard.utils.parsers import parse_quick_add
    # oben: importiere die funktion einmal statisch (empfohlen)
    from risk_dashboard.ui_helpers import add_tickers_and_fetch  # oder korrekter Pfad

    # oben idealerweise: from risk_dashboard.data_utils import add_tickers_and_fetch
    if st.sidebar.button("Hinzufügen", key=f"{prefix}_btn_add_tickers"):
        parsed = parse_quick_add(ticker_raw, default_qty=int(qty_default))
        if not parsed:
            st.warning("Keine gültigen Ticker erkannt.")
        else:
            # Normalisiere Ticker und baue tickers_with_qty
            tickers_with_qty = []
            for item in parsed:
                t = normalize_ticker(item["ticker"])
                q = int(item.get("quantity", int(qty_default)))
                if q <= 0:
                    continue
                tickers_with_qty.append((t, q))

            # Update portfolio in session_state (persistiert Mengen)
            portfolio = st.session_state.get("portfolio")
            if portfolio is None:
                portfolio = pd.DataFrame(columns=["ticker", "quantity"])
            for t, q in tickers_with_qty:
                if t in portfolio["ticker"].values:
                    portfolio.loc[portfolio["ticker"] == t, "quantity"] = (
                        portfolio.loc[portfolio["ticker"] == t, "quantity"].astype(int) + q
                    )
                else:
                    portfolio = pd.concat([portfolio, pd.DataFrame([{"ticker": t, "quantity": q}])], ignore_index=True)
            from risk_dashboard.ui_helpers import persist_portfolio_df
            # persistiere Portfolio
            persist_portfolio_df(portfolio)
            tickers = list({t for t, _ in tickers_with_qty})
            try:
                success, failed, combined = add_tickers_and_fetch(
                    tickers,
                    prefix=prefix,
                    start=DEFAULT_START_STR,
                    end=str(pd.Timestamp.today()),
                )
            except Exception:
                logger.exception("Konnte add_tickers_and_fetch nicht importieren/ausführen")
                st.error("Interner Fehler beim Laden der Preisdaten")
                success, failed, combined = [], [], pd.DataFrame()

            st.session_state["prices_for_bt"] = combined if (combined is not None and not combined.empty) else pd.DataFrame()

            if failed:
                st.warning(f"Keine Preisdaten für: {', '.join(failed)} (möglicherweise delisted)")
            if success:
                st.success(f"Erfolgreich geladen: {', '.join(success)}")

            logger.debug("add_tickers success=%s failed=%s", success, failed)

            prices = st.session_state.get("prices_for_bt")
            st.sidebar.write("DEBUG prices_for_bt cols", None if prices is None else list(prices.columns))
            if isinstance(prices, pd.DataFrame) and not prices.empty:
                st.sidebar.write("DEBUG prices head", prices.head())
                st.sidebar.write("DEBUG prices index range", prices.index.min(), prices.index.max())

            st.sidebar.write("DEBUG portfolio_df", st.session_state.get("portfolio_df"))

            st.session_state["navigate_to"] = "Holdings Analyse"
            safe_rerun(stop=False)
            
    st.sidebar.markdown("---")

    # ----- Einzel-Ticker Analyse (separates Feld) -----
    st.sidebar.subheader("Einzelticker analysieren")
    single_ticker = st.sidebar.text_input(
        "Ticker für Analyse (einzeln)", key="new_ticker", placeholder="z. B. AAPL oder CSPX.L"
    )
    if st.sidebar.button("Analysieren", key="analyze_main"):
        ticker = (single_ticker or "").strip().upper()
        if not ticker:
            st.sidebar.warning("Bitte ein Ticker-Kürzel eingeben.")
        else:
            if analyze_ticker is None:
                st.sidebar.error("Analyse-Funktion nicht verfügbar (Modul fehlt).")
            else:
                try:
                    analyze_ticker(ticker, available_etfs)
                except Exception as e:
                    st.sidebar.error(f"Analyse fehlgeschlagen: {e}")

    st.sidebar.markdown("---")

    # ----- Standard-ETFs (Auswahl) -----
    st.sidebar.subheader("Standard‑ETFs")
    st.sidebar.multiselect("LOW RISK", options=available_etfs, key="low_risk_selected")
    st.sidebar.multiselect("MEDIUM RISK", options=available_etfs, key="med_risk_selected")
    st.sidebar.multiselect("HIGH RISK", options=available_etfs, key="high_risk_selected")

    st.sidebar.markdown("---")

    # ----- Optimierungsverfahren Auswahl -----
    st.sidebar.selectbox(
        "Optimierungsverfahren wählen",
        ["HRP", "Mean-Variance", "Min-Var"],
        key="opt_method",
    )

render_sidebar(AVAILABLE_ETF)

st.title("Macroeconomic Risk Dashboard")

try:

    # zentral: Index auswählen und Universe einmalig laden
    prefix = "app"
    if ss.get("DEBUG"):
        st.text(f"DEBUG prefix: {prefix}")

    logger.debug("About to render index selectbox in %s with prefix=%s", __name__, prefix)
    index_choice = st.sidebar.selectbox(
        "Index / Universe wählen",
        list(UNIVERSE_PATHS.keys()),
        index=1,
        key=f"{prefix}_index_choice",
    )

    path_index_choice = UNIVERSE_PATHS[index_choice]
    etf_universe, universe_warnings = load_etf_universe(path_index_choice)
    # load shared data...

    # initialisiere shared session_state falls nötig
    if "macro_df" not in st.session_state:
        st.session_state["macro_df"] = load_and_validate_macro_data()
    if "price_data" not in st.session_state:
        st.session_state["price_data"] = load_price_data(etf_universe)

    # Übergabe an profile_form_ui

    if st.session_state.get("show_profile_editor", False):
        profile_form_ui(
                etf_universe=etf_universe,
                universe_warnings=universe_warnings,
                macro_df=st.session_state.get("macro_df"),
                price_data=st.session_state.get("price_data"),
                index_choice=index_choice,
                prefix=prefix
            )
    else:
        render_etf_tab()


except Exception:
    logging.getLogger(__name__).exception("profile_form_ui konnte nicht geladen werden")

# --- ETF Auswahl UI oben auf der Seite ---

# einmalige Initialisierung (falls nötig)
init_key = f"{prefix}_ui_initialized"
if not st.session_state.get(init_key, False):
    # nur Setup, keine Widgets
    st.session_state[init_key] = True
    logging.getLogger(__name__).debug("_ui_initialized initial setup done")

# immer rendern
try:
    from risk_dashboard.ui.etf_selection_ui import render_etf_selection_ui
    render_etf_selection_ui(prefix="etf")
except Exception as _e:
    logging.getLogger(__name__).exception("Fehler beim Rendern der ETF Auswahl UI oben: %s", _e)
    st.error("Interner Fehler beim Rendern. Details im Log.")


MACRO_LABELS = {
    "GDP": "GDP (Mrd. USD)",
    "CPI": "Inflation (CPI Index)",
    "UNRATE": "Arbeitslosenquote (%)",
    "FEDFUNDS": "Leitzins (%)",
    "PCE": "PCE Preisindex",
    "INDPRO": "Industrieproduktion (Index)",
    "RETAIL": "Einzelhandelsumsatz (Index)",
    "HOUSING": "Housing Starts (Tsd.)"
}

# UI Defaults and inputs
low_defaults = ["CSPX.L", "EUNL.DE"]
med_defaults = ["IMEU.L", "IQQ0.DE"]
high_defaults = ["AGGG.L", "SGLN.L"]

low_extra = st.text_input("Low Risk Zusätzliche ETF (kommagetrennt)", value="", key="input_low_extra")
med_extra = st.text_input("Medium Risk Zusätzliche ETF (kommagetrennt)", value="", key="input_med_extra")
high_extra = st.text_input("High Risk Zusätzliche ETF (kommagetrennt)", value="", key="input_high_extra")

low_etf = parse_etf_input(low_defaults, low_extra)
med_etf = parse_etf_input(med_defaults, med_extra)
high_etf = parse_etf_input(high_defaults, high_extra)

etf_universes = {
    "low": low_etf,
    "medium": med_etf,
    "high": high_etf
}

# Defensive Ersatz für: dates_rp = ensure_date_series(bt_rp); dates_hrp = ensure_date_series(bt_hrp)

def _safe_ensure_date_series(df, label="df"):
    # None / empty check
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        logging.getLogger(__name__).warning("%s is None", label)
        return pd.Series(dtype="datetime64[ns]")
    if hasattr(df, "empty") and df.empty:
        logging.getLogger(__name__).warning("%s is empty", label)
        return pd.Series(dtype="datetime64[ns]")
    # If DataFrame has a 'date' column
    if "date" in df.columns:
        try:
            s = pd.to_datetime(df["date"], errors="coerce")
            if not s.dropna().empty:
                return s
        except Exception:
            logging.getLogger(__name__).debug("Could not parse 'date' column for %s", label)
    # If index is DatetimeIndex
    if isinstance(df.index, pd.DatetimeIndex):
        try:
            s = pd.to_datetime(df.index, errors="coerce")
            if not s.dropna().empty:
                return s
        except Exception:
            logging.getLogger(__name__).debug("Index is DatetimeIndex but parsing failed for %s", label)
    # Try reset_index and find datetime column
    tmp = df.reset_index()
    datetime_cols = [c for c in tmp.columns if pd.api.types.is_datetime64_any_dtype(tmp[c])]
    if datetime_cols:
        try:
            s = pd.to_datetime(tmp[datetime_cols[0]], errors="coerce")
            if not s.dropna().empty:
                return s
        except Exception:
            logging.getLogger(__name__).debug("reset_index datetime column parse failed for %s", label)
    # Try to infer a date-like column by name
    candidates = [c for c in tmp.columns if any(k in c.lower() for k in ("date","time","ds"))]
    for c in candidates:
        try:
            s = pd.to_datetime(tmp[c], errors="coerce")
            if not s.dropna().empty:
                logging.getLogger(__name__).debug("Inferred date column '%s' for %s", c, label)
                return s
        except Exception:
            continue
    # Nothing found -> return empty series
    logging.getLogger(__name__).warning("Could not determine date series for %s (columns: %s)", label, list(df.columns))
    return pd.Series(dtype="datetime64[ns]")



# Tabs
tab_macro, tab_fx, tab_scenarios, tab_risk, tab_hmm, tab_invest, tab_lexikon = st.tabs(
    ["📈 Macro Data", "💱 FX Forecast", "🧪 Szenarien", "⚠️ Risiko", "HMM‑Regime", "📊 Investment", "📘 Lexikon"]
)

# ---------------------------------------------------------
# MACRO TAB
# ---------------------------------------------------------
with tab_macro:
    st.header("Macro Data (FRED)")

    st.info(
        "Makroserien sind ökonomische Zeitreihen wie GDP, CPI oder UNRATE. "
        "Sie beschreiben den Zustand einer Volkswirtschaft über die Zeit und sind zentral für Investment-Entscheidungen."
    )

    series = {
        "GDP": "Gross Domestic Product",
        "CPIAUCSL": "Consumer Price Index (Inflation)",
        "UNRATE": "Unemployment Rate",
        "FEDFUNDS": "Federal Funds Rate",
        "INDPRO": "Industrial Production Index",
        "PAYEMS": "Total Nonfarm Payrolls",
    }

    selected = st.selectbox(
        "Select macro series:",
        list(series.keys()),
        format_func=lambda x: series[x],
        help=get_definition("Makroserien"),
        key="profiles_select_macro_series"
    )

    macro_df = load_macro_series(selected)
    macro_df = macro_df.reset_index()

    st.subheader("Beschreibung der ausgewählten Makroserie")
    desc = get_definition(selected)
    st.write(desc if desc else "Keine Beschreibung verfügbar.")

    st.subheader("Investment-Zusammenhang (Aktien / ETF / Wertpapiere)")
    investment_relations = {
        "GDP": "Wirtschaftswachstum beeinflusst Unternehmensgewinne. Höheres GDP → tendenziell höhere Aktienkurse und ETF-Werte.",
        "CPIAUCSL": "Inflation treibt Zinsen. Hohe Inflation belastet Bewertungen, besonders Wachstums- und Tech-Aktien.",
        "UNRATE": "Hohe Arbeitslosigkeit schwächt Konsum und Unternehmensgewinne → Risiko für Aktienmärkte.",
        "FEDFUNDS": "Zinsen bestimmen Diskontierungsfaktoren. Höhere Zinsen → niedrigere Bewertungen von Aktien und Anleihen.",
        "INDPRO": "Steigende Industrieproduktion signalisiert reale Aktivität und Gewinnwachstum → positiv für zyklische Aktien.",
        "PAYEMS": "Mehr Beschäftigung stärkt Konsum und Nachfrage → stützt breite Aktienindizes und Konsum-ETF."
    }
    st.write(investment_relations.get(selected, "Kein direkter Investment-Zusammenhang hinterlegt."))

    fig = px.line(
        macro_df,
        x="date",
        y="value",
        title=f"{selected} – {series[selected]}",
        markers=True
    )
    fig.update_layout(
        height=500,
        yaxis_title=MACRO_LABELS.get(selected, "Wert")
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# FX FORECAST TAB
# ---------------------------------------------------------
with tab_fx:
    st.header("FX Forecast Module 2.0 (EUR/USD)")

    st.info(
        "Wechselkurse werden stark von Makrodaten beeinflusst: Zinsen, Inflation, Wachstum und Risiko. "
        "Das ist relevant für globale Aktien- und ETF-Portfolios."
    )

    model_choice = st.selectbox(
        "FX-Model:",
        ["ARIMA", "Prophet", "Both"],
        help="ARIMA = klassisches Zeitreihenmodell, Prophet = robustes Forecasting-Modell.",
        key="profiles_fx_model_choice"
    )

    hist_arima = fc_arima = hist_prophet = fc_prophet = pd.DataFrame()
    # weitere FX-Logik folgt hier...
    if model_choice in ["ARIMA", "Both"]:
        hist_arima, fc_arima = forecast_fx_arima(pair="EURUSD=X", period="10y", steps=60)
        if fc_arima is None or fc_arima.empty:
            st.warning("ARIMA-Forecast nicht verfügbar (keine Daten).")

    if model_choice in ["Prophet", "Both"]:
        hist_prophet, fc_prophet = forecast_fx_prophet(steps=60)
        if fc_prophet is None or fc_prophet.empty:
            st.warning("Prophet-Forecast nicht verfügbar (keine Daten).")

    fig = go.Figure()

    if model_choice in ["ARIMA", "Both"] and isinstance(hist_arima, pd.DataFrame) and not hist_arima.empty:
        if "date" in hist_arima.columns and "fx" in hist_arima.columns:
            fig.add_trace(go.Scatter(
                x=hist_arima["date"], y=hist_arima["fx"],
                mode="lines", name="Historical (ARIMA)"
            ))
    if model_choice in ["ARIMA", "Both"] and isinstance(fc_arima, pd.DataFrame) and not fc_arima.empty:
        if "date" in fc_arima.columns and "fx" in fc_arima.columns:
            fig.add_trace(go.Scatter(
                x=fc_arima["date"], y=fc_arima["fx"],
                mode="lines", name="Forecast (ARIMA)"
            ))

    if model_choice in ["Prophet", "Both"] and isinstance(hist_prophet, pd.DataFrame) and not hist_prophet.empty:
        if "ds" in hist_prophet.columns and "y" in hist_prophet.columns:
            fig.add_trace(go.Scatter(
                x=hist_prophet["ds"], y=hist_prophet["y"],
                mode="lines", name="Historical (Prophet)"
            ))
    if model_choice in ["Prophet", "Both"] and isinstance(fc_prophet, pd.DataFrame) and not fc_prophet.empty:
        if "ds" in fc_prophet.columns and "yhat" in fc_prophet.columns:
            fig.add_trace(go.Scatter(
                x=fc_prophet["ds"], y=fc_prophet["yhat"],
                mode="lines", name="Forecast (Prophet)"
            ))

    if not fig.data:
        st.info("Keine FX-Daten/Forecasts verfügbar zum Plotten.")
    else:
        fig.update_layout(
            title="EUR/USD Forecast",
            height=500,
            xaxis_title="Date",
            yaxis_title="EUR/USD"
        )
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------
# SCENARIOS TAB
# ---------------------------------------------------------
with tab_scenarios:
    st.header("Makro-Szenariovergleich")

    st.info("Vergleich zwischen Baseline und Szenario für alle Makrovariablen.")

    baseline_df = build_baseline_scenario()

    scenario_df = build_scenario(
        bip_shock=st.slider("BIP‑Schock", 0.7, 1.3, 1.0),
        inflation_shock=st.slider("Inflations‑Schock", 0.5, 2.0, 1.0),
        unemployment_shock=st.slider("Arbeitslosen‑Schock", 0.5, 2.0, 1.0),
        interest_shock=st.slider("Zins‑Schock", 0.5, 2.0, 1.0)
    )

    variables = sorted(scenario_df["variable_Label"].unique())

    fig = go.Figure()

    for var in variables:
        base = baseline_df[baseline_df["variable_Label"] == var]
        scen = scenario_df[scenario_df["variable_Label"] == var]

        fig.add_trace(go.Scatter(
            x=base["date"],
            y=base["value"],
            mode="lines",
            name=f"{var} – Baseline",
            line=dict(width=2)
        ))

        fig.add_trace(go.Scatter(
            x=scen["date"],
            y=scen["value"],
            mode="lines",
            name=f"{var} – Szenario",
            line=dict(width=2, dash="dash")
        ))

    fig.update_layout(
        title="Szenario vs. Baseline",
        xaxis_title="Datum",
        yaxis_title="Wert",
        height=700,
        template="plotly_white"
    )

    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------
# RISK, REGIME, HMM
# ---------------------------------------------------------
with tab_risk:
    st.header("Makro-Risiko-Score & Regime-Modell")

    risk_score_df = compute_risk_score_v2(normalize=True, method="minmax")
    if risk_score_df.empty:
        st.error("Keine Risiko-Daten verfügbar.")
        st.stop()

    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    col = next((c for c in preferred_cols if c in risk_score_df.columns), None)
    if col is None:
        st.error(f"Erwartete Spalte nicht gefunden. Vorhandene Spalten: {risk_score_df.columns.tolist()}")
        st.stop()

    latest = float(risk_score_df.iloc[-1][col])

    if not isinstance(risk_score_df.index, pd.DatetimeIndex) and "date" in risk_score_df.columns:
        risk_score_df["date"] = pd.to_datetime(risk_score_df["date"], errors="coerce")
        risk_score_df = risk_score_df.set_index("date")

    df_risk = risk_score_df.reset_index(drop=False)
    if col in df_risk.columns and len(df_risk) > 12:
        df_risk[f"{col}_shift12"] = df_risk[col].shift(12)
        one_year_ago = df_risk[f"{col}_shift12"].iloc[-1] if not pd.isna(df_risk[f"{col}_shift12"].iloc[-1]) else None
    else:
        one_year_ago = None

    col1, col2 = st.columns(2)
    col1.metric("Aktueller Risiko-Score", f"{latest:.3f}")
    if one_year_ago is not None:
        col2.metric("Veränderung 12M", f"{latest - one_year_ago:.3f}")
    else:
        col2.metric("Veränderung 12M", "nicht verfügbar")

    plot_df = df_risk.copy()
    if "date" not in plot_df.columns:
        plot_df = plot_df.reset_index().rename(columns={"index": "date"})
    plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
    plot_col = "risk_score" if "risk_score" in plot_df.columns else col

    if plot_df.empty or plot_col not in plot_df.columns:
        st.warning("Keine gültigen Daten für den Plot.")
    else:
        fig = px.line(plot_df, x="date", y=plot_col, title="Makro-Risiko-Score", markers=True)
        fig.update_layout(height=500, yaxis_title="Risk Score")
        st.plotly_chart(fig, width='stretch')

    st.info(
        "Der PCA-basierte Risiko-Score fasst mehrere Makrovariablen zu einer einzigen Risikokomponente zusammen."
    )

    st.subheader("Regime-Modell (Markov)")

    if not isinstance(risk_score_df.index, pd.DatetimeIndex) and "date" in risk_score_df.columns:
        risk_score_df["date"] = pd.to_datetime(risk_score_df["date"], errors="coerce")
        risk_score_df = risk_score_df.set_index("date")
    risk_score_series = risk_score_df[col]

    if risk_score_series.empty:
        st.warning("Keine Risiko-Score-Serie vorhanden.")
        st.stop()

    current_score = float(risk_score_series.iloc[-1])
    current_regime = classify_regime_from_score(current_score)
    st.metric("Aktuelles Makro-Szenario", current_regime)

    regime_df = build_regime_timeline(risk_score_series)
    trans_matrix = compute_regime_transition_matrix(regime_df)

    st.subheader("Regime-Transitionsmatrix")
    st.dataframe(trans_matrix.style.format("{:.2f}"))

    next_dist = next_regime_distribution(current_regime, trans_matrix)
    st.subheader("Wahrscheinlichkeit nächstes Regime")
    st.bar_chart(next_dist)

with tab_hmm:
    st.header("HMM-Regime-Modell")

    try:
        macro_df  # prüft Existenz
    except NameError:
        st.error("Makro-Daten (macro_df) nicht gefunden. Bitte zuerst Macro Data laden.")
    else:
        hmm_model, hmm_regime_df = fit_hmm_regimes(macro_df, n_states=3)
        hmm_regime_df, label_map, best_col = map_hmm_states_to_labels(hmm_regime_df)

        st.subheader("HMM-Regime-Zeitverlauf")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hmm_regime_df.index,
            y=hmm_regime_df[best_col],
            mode="lines",
            name=f"{best_col}"
        ))

        for state, label in label_map.items():
            sub = hmm_regime_df[hmm_regime_df["hmm_state"] == state]
            if not sub.empty:
                fig.add_vrect(
                    x0=sub.index.min(),
                    x1=sub.index.max(),
                    fillcolor="lightgreen" if "Boom" in label else "lightgray",
                    opacity=0.15,
                    layer="below",
                    line_width=0,
                )

        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------
# INVESTMENT TAB
# ---------------------------------------------------------
with tab_invest:
    st.header("Investition – Makro-Regime, Portfolio & Backtests")

    with st.expander("Makro-Investment-Kochrezept – Wie dieses System funktioniert", expanded=True):
        st.markdown(
            """
            ### 1. Regime erkennen
            Makrodaten → Risk Score → Low / Medium / High Risk

            ### 2. ETF‑Universum pro Regime auswählen
            Jedes Regime hat eigene ETF‑Typen

            ### 3. Optimierungsmethode wählen
            - Risk Parity; - HRP (Hierarchical Risk Parity)

            ### 4. Portfolio pro Regime bauen
            Gewichte werden pro Regime berechnet

            ### 5. Backtesten
            Historische Regime + ETF‑Daten → Equity‑Kurve

            ### 6. Performance analysieren
            Sharpe, Volatilität, Drawdown

            ### 7. Optimieren
            ETF‑Universen, Regime‑Definitionen, Optimierungsverfahren
            """
        )

    st.subheader("Gesamtprozess Von Makro zu Portfolio")
    st.code(
        """
Makrodaten → FX‑Modell → Risiko‑Score → Szenario → Regime → Portfolio → Investment‑Paket
[ Makro-Panel ] Inflation, Wachstum, PMI, Arbeitsmarkt
[ FX-Panel ] USD-Trend, FX‑Volatilität
[ Risiko-Score ] 0.0 (Risk‑Off) … 1.0 (Risk‑On)
[ Szenarien ] Rezession, Stagflation, Soft Landing, Reflation, Boom
[ Regime ] Low / Medium / High Risk
[ Portfolio ] Risk Parity / HRP / Benchmark
[ Investment-Paket ] ETF‑Mix, Gold/Rohstoffe, Hedge, Risiko‑Budget
        """
    )
    st.markdown("---")

    # FX- und Markt-Risikofaktoren erzeugen (defensive)
    try:
        fx_prices = download_fx_history(["DX-Y.NYB"], period="10y")
        fx_df = build_fx_risk_factors(fx_prices)
    except Exception:
        logging.getLogger(__name__).exception("Fehler beim Laden/Verarbeiten von FX-Daten")
        fx_prices = pd.DataFrame()
        fx_df = pd.DataFrame()

    try:
        etf_prices = download_etf_history(["EUNL.DE"], period="10y")
    except Exception:
        logging.getLogger(__name__).exception("Fehler beim Laden von ETF-Daten")
        etf_prices = pd.DataFrame()

    try:
        prices_norm = normalize_price_df(etf_prices)
    except Exception:
        logging.getLogger(__name__).exception("normalize_price_df schlug fehl")
        prices_norm = pd.DataFrame()

    missing = []
    if isinstance(etf_prices, pd.DataFrame) and isinstance(prices_norm, pd.DataFrame):
        missing = [c for c in etf_prices.columns if c not in prices_norm.columns]
        for t in missing:
            st.warning(f"{t}: DataFrame ohne 'Close' Spalte — wird übersprungen.")

    etf_prices = prices_norm.copy() if not prices_norm.empty else pd.DataFrame()

    try:
        market_df = build_market_risk_factors(etf_prices) if not etf_prices.empty else pd.DataFrame()
    except Exception:
        logging.getLogger(__name__).exception("build_market_risk_factors schlug fehl")
        market_df = pd.DataFrame()

    # Risiko-Score & Szenario
    risk_score_df = compute_risk_score_v2(normalize=True, method="minmax")
    if risk_score_df.empty:
        st.error("Keine Risiko-Daten verfügbar.")
        st.stop()

    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    col = next((c for c in preferred_cols if c in risk_score_df.columns), None)
    if col is None:
        st.error(f"Erwartete Spalte nicht gefunden. Vorhandene Spalten: {risk_score_df.columns.tolist()}")
        st.stop()

    latest = float(risk_score_df.iloc[-1][col])

    scenario_df = build_scenario_series(risk_score_df)
    if scenario_df.empty:
        st.warning("scenario_df ist leer. Backtests/Plots werden nicht erstellt.")
        st.stop()

    scenario_regimes = scenario_df.copy().rename(columns={"scenario": "regime"})
    scenario_regimes = ensure_date_column(scenario_regimes)
    if "date" not in scenario_regimes.columns and isinstance(scenario_regimes.index, pd.DatetimeIndex):
        scenario_regimes = scenario_regimes.reset_index().rename(columns={"index": "date"})
    if "date" in scenario_regimes.columns:
        scenario_regimes["date"] = pd.to_datetime(scenario_regimes["date"], errors="coerce")

    # nachdem scenario_df und scenario_regimes berechnet wurden
    st.session_state["scenario_df"] = scenario_df
    st.session_state["scenario_regimes"] = scenario_regimes

    
    st.write("DEBUG cols:", risk_score_df.columns.tolist())
    st.write("DEBUG head:", risk_score_df.head())
    st.write("DEBUG scenario_df head:", scenario_df.head())

    current_date = scenario_df.index[-1]
    current_risk_score = float(scenario_df["risk_score"].iloc[-1])
    current_scenario = scenario_df["scenario"].iloc[-1]

    st.metric(label="Aktueller Risiko-Score (0–1)", value=f"{current_risk_score:.2f}")
    st.metric(label="Aktuelles Makro-Szenario", value=current_scenario)

    fig_risk = px.line(scenario_df, y="risk_score", title="Risiko-Score – Zeitverlauf")
    fig_risk.update_layout(height=300)
    st.plotly_chart(fig_risk, width="stretch")

    fig_scen = px.scatter(scenario_df, y="scenario", title="Makro-Szenario – Zeitverlauf", color="scenario")
    fig_scen.update_layout(height=300)
    st.plotly_chart(fig_scen, width="stretch")

    st.markdown("---")

    # Regelbasiertes Makro-Portfolio
    st.subheader("Regelbasiertes Makro-Portfolio (Investment-Modul 3.0)")

    risk_budget = st.slider(
        "Risiko-Budget (Investitionsgrad)",
        0.0, 1.0, 1.0, 0.1,
        help="0.5 = 50% des Kapitals investiert, 50% Cash."
    )

    try:
        result = investment_recommendations_v3(risk_budget=risk_budget)
    except Exception:
        logging.getLogger(__name__).exception("investment_recommendations_v3 schlug fehl")
        result = {"macro_trends": {}, "risk_level": None, "regime": None, "risk_budget": risk_budget, "weights": {}, "etf_mapping": {}}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Makro-Trends & Regime")
        st.write(result.get("macro_trends", {}))
        st.write("Risk Level:", result.get("risk_level"))
        st.write("Regime:", result.get("regime"))
        st.write("Risiko-Budget:", result.get("risk_budget"))

    with col2:
        st.subheader("Portfolio-Gewichtung (regelbasiert)")
        st.write(result.get("weights", {}))
        st.subheader("ETF-Mapping")
        for asset, etfs in result.get("etf_mapping", {}).items():
            st.markdown(f"**{asset}**")
            for e in etfs:
                st.markdown(f"- {e}")

    st.markdown("---")
    st.subheader("Regime-basierte Handelsstrategie")
    try:
        strat = regime_based_strategy()
        st.write(f"Aktuelles Regime: **{strat.get('regime')}**")
        st.write("Bevorzugte Assetklassen:")
        for a in strat.get("preferred_assets", []):
            st.markdown(f"- {a}")
    except Exception:
        logging.getLogger(__name__).exception("regime_based_strategy schlug fehl")
        st.write("Strategie nicht verfügbar")

    # ETF-Backtest (Regime-basiert)
    st.markdown("---")
    st.subheader("Backtest 2.0 mit echten ETF-Daten")
    st.info("Hinweis: Hier werden beispielhafte ETF-Ticker verwendet. Du kannst sie später anpassen.")


    from risk_dashboard.core.holdings import get_holdings_for_etf, map_holdings_to_pricecols

    # --- Konfiguration / Defaults ---
    start = DEFAULT_START_STR
    end = None

    # Beispiel: wenn du mehrere ETF‑Sets testen willst, iteriere später über ticker_map.
    ticker_map = {
        "Low Risk": ["CSPX.L", "EUNL.DE"],
        "Medium Risk": ["IMEU.L", "IQQ0.DE"],
        "High Risk": ["AGGG.L", "SGLN.L"],
    }

    # Wähle hier den ETF, dessen Holdings du laden willst (ein String, nicht ticker_map)
    etf_ticker = "CSPX.L"  # <-- Korrigiert: einzelner ETF-Ticker

    # Load holdings
    hold = get_holdings_for_etf(etf_ticker, api_key=None)
    holdings_list = list(dict.fromkeys(hold["ticker"].astype(str).tolist())) if not hold.empty else []

    # Universe: entweder Holdings oder Fallback auf alle ETF-Ticker aus ticker_map
    tickers_for_universe = holdings_list or [t for group in ticker_map.values() for t in group]

    # Preise laden
    used, prices = fetch_prices_quiet_with_used(tickers_for_universe, start=start, end=end)

    # Mapping versuchen
    mapped_cols, missing = map_holdings_to_pricecols(holdings_list, prices.columns)


   # --- Safety: remove any accidental browser dump from file manually before running ---

    # Ensure session keys are initialized BEFORE widgets that use them
    if stable_input_key not in st.session_state:
        st.session_state[stable_input_key] = ""

    # (sidebar code creates the widget)
    # st.text_input("Ticker hinzufügen", key=stable_input_key, placeholder="z.B. AAPL oder VWRL")

    # --- Mapping UI block (after mapped_cols, missing computed) ---
    if "manual_map" not in st.session_state:
        st.session_state.manual_map = {}

    # initialize holding_to_price from any existing mapping
    holding_to_price = {h: c for h, c in zip(holdings_list, mapped_cols)} if mapped_cols else {}

    # guard: prices must exist
    if prices is None or getattr(prices, "empty", True):
        st.error("Keine Preisdaten verfügbar. Prüfe Ticker und Datenquelle.")
    else:
        # --- Holdings Upload + Manual Mapping + Persistierung für Backtest ---
        if "mapping_missing" not in st.session_state:
            st.session_state["mapping_missing"] = []
        if "weights_by_pricecol" not in st.session_state:
            st.session_state["weights_by_pricecol"] = {}

        # Prüfe session state
        # st.sidebar.write("session keys:", list(st.session_state.keys()))
        st.sidebar.write("user_tickers:", st.session_state.get("user_tickers"))
        st.sidebar.write("portfolio_df (head):", st.session_state.get("portfolio_df").head() if st.session_state.get("portfolio_df") is not None else "None")

        # Prüfe price cache / prices_for_bt
        st.sidebar.write("prices_for_bt keys:", list(st.session_state.get("prices_for_bt", {}).keys()) if isinstance(st.session_state.get("prices_for_bt"), dict) else "not-dict")
        st.sidebar.write("prices_for_bt sample:", st.session_state.get("prices_for_bt"))

        st.markdown("### Optional: Holdings hochladen (CSV mit Spalte 'ticker')")

        uploaded = show_holdings_uploader(prefix="profile")
        st.write("DEBUG: uploaded object:", bool(uploaded))

        if uploaded is not None:
            try:
                # Lese die Datei einmal und persistiere DataFrame
                uploaded.seek(0)
                uploaded_df = pd.read_csv(uploaded)
                st.write("DEBUG: uploaded_df head:", uploaded_df.head())

                # Falls portfolio_df noch nicht gesetzt ist, setze es
                if "portfolio_df" not in st.session_state:
                    st.session_state["portfolio_df"] = uploaded_df

                if "ticker" in uploaded_df.columns:
                    holdings_list = list(dict.fromkeys(uploaded_df["ticker"].astype(str).tolist()))
                    mapped_cols, missing_local = do_add_tickers(holdings_list, prefix, asset_key, prices=prices)
                    st.session_state["mapping_missing"] = missing_local or []
                    st.session_state["last_uploaded_holdings"] = holdings_list
                    logger.debug("do_add_tickers -> mapped_cols=%s missing=%s", mapped_cols, missing_local)
                    safe_rerun(stop=False)
                else:
                    st.error("Hochgeladene CSV enthält keine Spalte 'ticker'.")
            except Exception as e:
                logger.exception("Fehler beim Einlesen der hochgeladenen Datei: %s", e)
                st.error(f"Fehler beim Einlesen der Datei: {e}")

        # Manual mapping UI (only if there are missing tickers)
        missing = st.session_state.get("mapping_missing", []) or []

        if missing:
            st.warning(f"Automatisches Mapping fehlgeschlagen für: {', '.join(missing)}")
            cols = ["<skip>"] + list(prices.columns)

            # Use a form so all selectboxes are submitted together
            with st.form("manual_map_form"):
                for h in missing:
                    default = st.session_state.get("manual_map", {}).get(h, "<skip>")
                    st.selectbox(
                        f"Map {h} →",
                        options=cols,
                        index=cols.index(default) if default in cols else 0,
                        key=f"map_{h}"
                    )
                submitted = st.form_submit_button("Apply manual mapping")

            if submitted:
                st.session_state["_processing_apply_mapping"] = True
                try:
                    manual_map = st.session_state.get("manual_map", {}) or {}
                    for h in missing:
                        # read selection from the form keys
                        sel_key = f"map_{h}"
                        mapped_val = st.session_state.get(sel_key, "<skip>")
                        if mapped_val and mapped_val != "<skip>":
                            manual_map[h] = mapped_val
                    # persist manual_map back to session_state
                    st.session_state["manual_map"] = manual_map
                    # set a flag so the rest of the flow picks up the manual mapping
                    st.success("Manuelles Mapping angewendet.")
                finally:
                    st.session_state["_processing_apply_mapping"] = False

        # If weights_by_pricecol was persisted (either by do_add_tickers or manual mapping), build prices_for_bt and weights_by_ticker
        weights_by_pricecol = st.session_state.get("weights_by_pricecol", {}) or {}
        if weights_by_pricecol:
            unique_cols = list(weights_by_pricecol.keys())
            # normalize prices columns
            prices.columns = [str(c).strip() for c in prices.columns]
            missing_cols = [c for c in unique_cols if c not in prices.columns]
            if missing_cols:
                st.error(f"Die folgenden Price‑Spalten fehlen in den Preisdaten: {missing_cols}")
            else:
                prices_for_bt = prices.loc[:, unique_cols]

                # Build weights_by_ticker and normalize
                weights_by_ticker = {col: float(w) for col, w in weights_by_pricecol.items()}
                total = sum(weights_by_ticker.values()) or 0.0
                if total > 0:
                    weights_by_ticker = {col: (w / total) for col, w in weights_by_ticker.items()}
                else:
                    cols_list = list(weights_by_ticker.keys())
                    if cols_list:
                        eq_w = 1.0 / len(cols_list)
                        weights_by_ticker = {c: eq_w for c in cols_list}
                    else:
                        weights_by_ticker = {}

                # persist for backtest
                st.session_state["prices_for_bt"] = prices_for_bt
                st.session_state["weights_by_ticker"] = weights_by_ticker
                logger.debug("Manual mapping applied: prices_for_bt cols=%s weights_by_ticker=%s",
                            list(prices_for_bt.columns), weights_by_ticker)

                # trigger rerun so the top-of-function backtest check can pick up the keys
                safe_rerun(stop=False)

    # --- Danach: Backtest aufrufen (wie bisher) ---

    # 2) Aufruf innerhalb einer Funktion / UI‑Handler (z. B. in profile_form_ui)

    # --- Hauptblock: Backtest nur ausführen, wenn Preise und Gewichte vorhanden sind ---
    # oben im Modul (falls noch nicht importiert)

    # --- Backtest Ausführung nur wenn Preise und Gewichte vorhanden sind ---
    if "prices_for_bt" in st.session_state and "weights_by_ticker" in st.session_state:
        # Lese aus session_state (sichere .get Verwendung)
        prices_for_bt = st.session_state.get("prices_for_bt")
        weights_by_ticker = st.session_state.get("weights_by_ticker", {})

        # Defensive Prüfung
        if is_prices_empty(prices_for_bt) or not weights_by_ticker:
            st.error("Keine Preisdaten oder Gewichte vorhanden. Bitte lade Preisdaten oder wähle ETFs.")
            st.stop()

        # Normalisiere prices_for_bt zu DataFrame und schreibe zurück in session_state
        prices_for_bt = normalize_prices(prices_for_bt)
        st.session_state["prices_for_bt"] = prices_for_bt

        # Debug‑Log (nur logger)
        logger.debug(
            "Preparing backtest: prices_for_bt type=%s shape=%s weights_count=%d",
            type(prices_for_bt),
            getattr(prices_for_bt, "shape", None),
            len(weights_by_ticker),
        )

        # Import und Backtest-Aufruf
        from risk_dashboard.core.backtest import run_backtest_flow

        ss = st.session_state
        prefix = "profile"

        try:
            bt_etf = run_backtest_flow(
                ss=ss,
                prefix=prefix,
                price_data=prices_for_bt,
                weights_map=weights_by_ticker,
                min_common_days=250,
                initial_cash=ss.get("initial_cash", 100000),
                strategy=ss.get("selected_strategy", "equal"),
                rebalance=ss.get("rebalance", "monthly"),
            )
        except Exception as e:
            logger.exception("Backtest-Aufruf fehlgeschlagen", exc_info=True)
            st.error(f"Backtest fehlgeschlagen: {e}")
            st.stop()

        # --- Defensive Vereinheitlichung der Rückgabe ---
        # bt_etf kann ein Envelope-dict, ein DataFrame oder ein anderes Objekt sein.
        # Ziel: resp ist immer ein dict mit keys: ok, message, result, payload
        if isinstance(bt_etf, dict) and any(k in bt_etf for k in ("ok", "result", "payload")):
            resp = bt_etf
        else:
            # Wenn dict ohne Envelope-Struktur geliefert wurde, versuche result/payload zu extrahieren
            if isinstance(bt_etf, dict):
                resp = {
                    "ok": True,
                    "message": None,
                    "result": bt_etf.get("result", bt_etf),
                    "payload": bt_etf.get("payload", {}),
                }
            else:
                # bt_etf ist kein dict (z.B. DataFrame). Packe es als result in ein Envelope
                resp = {"ok": True, "message": None, "result": bt_etf, "payload": {}}

        logger.debug("BACKTEST RESULT ENVELOPE keys=%s", list(resp.keys()))
        st.json({k: resp.get(k) for k in ("ok", "message")})

        # --- Sichere Extraktion ohne Truth-Evaluation von DataFrames ---
        payload = resp.get("payload", {}) or {}
        res = resp.get("result", {}) if resp.get("result", None) is not None else {}

        # Wenn result serialisierte DataFrame-Repräsentation enthält, rekonstruiere sie
        if isinstance(res, dict) and res.get("__type") == "dataframe":
            df_rows = res.get("rows", [])
            try:
                df = pd.DataFrame(df_rows)
                st.dataframe(df)
            except Exception:
                st.write("Backtest result (table) — konnte nicht als DataFrame dargestellt werden.")

        # Wenn result ein dict mit portfolio_value enthält, plotte es sicher
        elif isinstance(res, dict) and "portfolio_value" in res:
            pv = res["portfolio_value"]
            try:
                st.line_chart(pd.DataFrame(pv))
            except Exception:
                st.write("Portfolio value vorhanden, aber konnte nicht geplottet werden.")

        # Wenn result bereits ein DataFrame ist, zeige/plotte es defensiv
        elif hasattr(res, "shape") and hasattr(res, "columns"):
            try:
                # optional: prüfe auf 'date' Spalte, aber nicht mit `if res:` vermeiden
                if "date" not in res.columns:
                    logger.warning("Backtest result missing 'date' column")
                st.line_chart(res)
                st.dataframe(res.head(200))
            except Exception:
                st.write("Backtest lieferte ein DataFrame, konnte aber nicht vollständig dargestellt werden.")

        # Trades anzeigen (payload oder result)
        trades = None
        if isinstance(payload, dict):
            trades = payload.get("trades")
        if trades is None and isinstance(res, dict):
            trades = res.get("trades")

        if trades:
            try:
                trades_df = pd.DataFrame(trades)
                st.dataframe(trades_df)
                if not trades_df.empty:
                    csv = trades_df.to_csv(index=False)
                    st.download_button("Export trades CSV", data=csv, file_name="trades.csv")
            except Exception:
                st.write("Trades vorhanden, aber konnten nicht als Tabelle dargestellt werden.")

        # Fehler-/Statusbehandlung des Envelope
        if not isinstance(resp, dict):
            resp = {"ok": False, "message": "Unerwartetes Backtest-Format", "result": {}, "payload": {}}

        if not resp.get("ok"):
            st.error(resp.get("message", "Backtest fehlgeschlagen"))
            removed = (resp.get("payload") or {}).get("removed") or (resp.get("payload") or {}).get("removed_tickers") or []
            if removed:
                st.warning("Entfernte Ticker: " + ", ".join(removed))
            if (resp.get("payload") or {}).get("common_shape"):
                st.info(f"Gemeinsame Handelstage: {resp['payload']['common_shape']}")

        # Logging: sichere, begrenzte Ausgabe
        logger.debug("BACKTEST CALL ARGS: weights_by_ticker=%s", weights_by_ticker)
        logger.debug("BACKTEST RESULT ENVELOPE (truncated): %s", repr(resp)[:2000])


        # Sichere Inspektion von portfolio_value (nur wenn dict)
        pv = None
        metrics = {}
        if isinstance(res, dict):
            pv = res.get("portfolio_value")
            metrics = res.get("metrics", {})

        logger.debug("portfolio_value type=%s shape=%s", type(pv), getattr(pv, "shape", None))
        try:
            nunique = pv.nunique() if hasattr(pv, "nunique") else None
            std = float(pv.std()) if hasattr(pv, "std") else None
            logger.debug("portfolio_value nunique=%s std=%s", nunique, std)
        except Exception:
            logger.exception("Error inspecting portfolio_value")
    else:
        bt_etf = backtest_etf_regime_portfolio(
            ticker_map,
            period="10y",
            scenario_df=scenario_df,
            scenario_regimes=scenario_regimes
        ) 
    
    st.write("DEBUG etf_prices:", etf_prices)
    st.write("DEBUG bt_etf (vor Anpassung):", bt_etf)

    # --- 1) Vereinheitliche bt_etf in ein DataFrame df_bt (defensiv) ---
    df_bt = None


    if isinstance(bt_etf, dict):
        from risk_dashboard.data_utils import sanitize_bt_etf
        bt_safe = sanitize_bt_etf(bt_etf)
        candidate = bt_safe.get("result") or bt_safe.get("payload") or bt_safe
        logging.debug("bt_etf sanitized keys=%s", list(bt_safe.keys()))
        # weiterverarbeitung mit candidate ...
        logging.debug(
            "BACKTEST RESULT ENVELOPE (truncated): ok=%s message=%s payload_keys=%s result_type=%s",
            bt_safe.get("ok"),
            (bt_safe.get("message")[:200] + "...") if isinstance(bt_safe.get("message"), str) and len(bt_safe.get("message"))>200 else bt_safe.get("message"),
            list(bt_safe.get("payload", {}).keys()) if isinstance(bt_safe.get("payload"), dict) else None,
            type(bt_safe.get("result")).__name__
        )

        try:
            if isinstance(candidate, pd.DataFrame):
                df_bt = candidate.copy()
            elif isinstance(candidate, list):
                df_bt = pd.DataFrame(candidate)
            elif isinstance(candidate, dict):
                # 1) serialisierte DataFrame-Repräsentation?
                if candidate.get("__type") == "dataframe" and isinstance(candidate.get("rows"), list):
                    df_bt = pd.DataFrame(candidate["rows"])
                else:
                    # 2) Wenn alle Werte Sequenzen gleicher Länge sind -> dict-of-columns
                    vals = list(candidate.values())
                    if vals and all(isinstance(v, (list, tuple, np.ndarray, pd.Series)) for v in vals):
                        lengths = [len(v) for v in vals]
                        if len(set(lengths)) == 1:
                            try:
                                df_bt = pd.DataFrame(candidate)
                            except Exception:
                                logger.exception("dict->DataFrame failed despite uniform lengths")
                                df_bt = pd.DataFrame()
                        else:
                            # unterschiedliche Längen -> nicht tabellarisch
                            logger.debug("Candidate dict has sequence values but differing lengths: %s", lengths)
                            df_bt = pd.DataFrame()
                    else:
                        # 3) Falls ein bekanntes Feld mit tabellarischen Daten existiert, extrahiere es
                        if "portfolio_value" in candidate:
                            pv = candidate["portfolio_value"]
                            if isinstance(pv, pd.DataFrame):
                                df_bt = pv.copy()
                            elif isinstance(pv, list):
                                # Liste von (date, value) oder Liste von Werten
                                try:
                                    df_bt = pd.DataFrame(pv)
                                except Exception:
                                    df_bt = pd.DataFrame({"portfolio_value": pv})
                            else:
                                df_bt = pd.DataFrame()
                        elif "trades" in candidate and isinstance(candidate["trades"], list):
                            try:
                                df_bt = pd.DataFrame(candidate["trades"])
                            except Exception:
                                df_bt = pd.DataFrame()
                        else:
                            # 4) Keine tabellarische Struktur erkennbar
                            logger.debug("Candidate dict is not tabular and contains keys: %s", list(candidate.keys()))
                            df_bt = pd.DataFrame()
            else:
                df_bt = pd.DataFrame()
        except Exception:
            logger.exception("Could not convert backtest candidate to DataFrame")
    elif hasattr(bt_etf, "shape") and hasattr(bt_etf, "columns"):
        df_bt = bt_etf.copy()

    if df_bt is None:
        logger.debug("bt_etf not tabular; using empty DataFrame for safe handling.")
        df_bt = pd.DataFrame()

    # --- 2) Sichere 'date' Erkennung, Konvertierung und Plotten (nur auf df_bt) ---
    if df_bt.empty:
        st.warning("Backtest lieferte keine tabellarischen Ergebnisse (leeres DataFrame). Kein Plot.")
    else:
        # finde/benenne alternative Datumsspalte
        if "date" not in df_bt.columns:
            alt_date_cols = [c for c in df_bt.columns if "date" in c.lower() or "time" in c.lower()]
            if alt_date_cols:
                df_bt = df_bt.rename(columns={alt_date_cols[0]: "date"})
                st.write(f"DEBUG: Umbenannt {alt_date_cols[0]} -> 'date'")
            else:
                tmp = df_bt.reset_index()
                datetime_cols = [c for c in tmp.columns if pd.api.types.is_datetime64_any_dtype(tmp[c])]
                if datetime_cols:
                    df_bt = tmp.rename(columns={datetime_cols[0]: "date"})
                    st.write(f"DEBUG: reset_index ergab datetime Spalte {datetime_cols[0]} -> 'date'")
                else:
                    st.error("Keine 'date'-Spalte oder Datetime-Index gefunden. Kein Plot.")
                    st.write("DEBUG df_bt info:", tmp.info())
                    df_bt = pd.DataFrame()

        # konvertiere Datum sicher, drop NaT, sortiere
        if not df_bt.empty and "date" in df_bt.columns:
            df_bt = df_bt.copy()  # vermeidet SettingWithCopyWarning
            df_bt["date"] = pd.to_datetime(df_bt["date"], errors="coerce")
            df_bt = df_bt.dropna(subset=["date"])
            if df_bt.empty:
                st.warning("Nach Datumskonvertierung keine gültigen Zeilen mehr.")
            else:
                df_bt = df_bt.sort_values("date").reset_index(drop=True)
                st.write("DEBUG df_bt (final):", df_bt.head())

                # Wähle y-Spalte: equity bevorzugt, sonst portfolio_value
                y_col = "equity" if "equity" in df_bt.columns else ("portfolio_value" if "portfolio_value" in df_bt.columns else None)
                if y_col is None:
                    st.error("Weder 'equity' noch 'portfolio_value' in den Daten. Kein Plot.")
                else:
                    try:
                        fig_bt2 = px.line(
                            df_bt,
                            x="date",
                            y=y_col,
                            color="regime" if "regime" in df_bt.columns else None,
                            title="Regime-basierte Equity-Kurve (ETF-Backtest)"
                        )
                        fig_bt2.update_layout(height=500, yaxis_title="Equity (indexiert)")
                        st.plotly_chart(fig_bt2, use_container_width=True)
                    except Exception:
                        logger.exception("Fehler beim Erstellen des Plotly-Figures")
                        st.error("Fehler beim Erstellen des Plots.")

    # --- 3) Performance-Kennzahlen nur aus df_bt berechnen ---
    if not df_bt.empty:
        stats_etf = performance_stats(df_bt)
        st.subheader("Performance-Kennzahlen (ETF-Backtest)")
        st.write(stats_etf)
    else:
        st.info("Keine Performance-Kennzahlen, da Backtest keine Daten lieferte.")

    st.markdown("---")
    st.subheader("ETF-Universen pro Regime konfigurieren")

    col_lr, col_mr, col_hr = st.columns(3)

    with col_lr:
        st.markdown("### Low Risk")
        low_multiselect = st.multiselect(
            "Standard-ETF auswählen",
            AVAILABLE_ETF,
            default=["CSPX.L", "EUNL.DE"],
            key="low_multi"
        )
        low_custom = st.text_input("Zusätzliche ETF (kommagetrennt)", "", key="low_custom")
        low_final = low_multiselect + [x.strip() for x in low_custom.split(",") if x.strip()]

    with col_mr:
        st.markdown("### Medium Risk")
        med_multiselect = st.multiselect(
            "Standard-ETF auswählen",
            AVAILABLE_ETF,
            default=["IMEU.L", "IQQ0.DE"],
            key="med_multi"
        )
        med_custom = st.text_input("Zusätzliche ETF (kommagetrennt)", "", key="med_custom")
        med_final = med_multiselect + [x.strip() for x in med_custom.split(",") if x.strip()]

    with col_hr:
        st.markdown("### High Risk")
        high_multiselect = st.multiselect(
            "Standard-ETF auswählen",
            AVAILABLE_ETF,
            default=["AGGG.L", "SGLN.L"],
            key="high_multi"
        )
        high_custom = st.text_input("Zusätzliche ETF (kommagetrennt)", "", key="high_custom")
        high_final = high_multiselect + [x.strip() for x in high_custom.split(",") if x.strip()]

    # Orchestrator already defined at top-level: get_investment_package

    st.markdown("---")
    st.subheader("Investment-Modul 4.0/5.0 – Regime-gesteuertes Optimierungsportfolio")

    opt_method = st.session_state.get("opt_method", "HRP")

    missing_rp = []
    missing_hrp = []

    if opt_method in ["Risk Parity", "RP", "Mean-Variance", "Risk-Parity", "Risk Parity"]:
        bt_opt, opt_struct, missing_rp = backtest_regime_risk_parity(
            low_final, med_final, high_final,
            period="10y",
            scenario_df=scenario_df,
            scenario_regimes=scenario_regimes
        )
        st.info("Aktiv: Regime-gesteuertes Risk-Parity-Portfolio.")
        if hasattr(bt_opt, "head"):
            st.write("DEBUG – RP Backtest Ergebnis (Head):", bt_opt.head())
    else:
        bt_opt, opt_struct, missing_hrp = backtest_regime_hrp(
            low_final, med_final, high_final,
            period="10y",
            scenario_df=scenario_df,
            scenario_regimes=scenario_regimes
        )
        st.info("Aktiv: Regime-gesteuertes Hierarchical Risk Parity (HRP)-Portfolio.")

    missing_total = sorted(set(missing_rp) | set(missing_hrp))
    if missing_total:
        st.warning(
            "Folgende ETF-Ticker konnten nicht geladen werden und wurden im Backtest ignoriert: "
            + ", ".join(missing_total)
        )

    if bt_opt is None or getattr(bt_opt, "empty", False):
        st.error("Backtest liefert keine Daten – keine gemeinsamen Monatsenden zwischen Returns und Regimen.")
        st.stop()

    # Robust: Datum aus bt_opt bestimmen
    if "date" in bt_opt.columns:
        bt_opt_dates = pd.to_datetime(bt_opt["date"], errors="coerce")
    elif isinstance(bt_opt.index, pd.DatetimeIndex):
        bt_opt_dates = pd.to_datetime(bt_opt.index)
    else:
        st.error("bt_opt enthält keine Datumsinformationen.")
        st.stop()

    if bt_opt_dates.isna().all():
        st.error("bt_opt enthält nur ungültige Datumswerte.")
        st.stop()

    current_date = bt_opt_dates.iloc[-1]

    if "regime" in bt_opt.columns:
        current_regime = bt_opt["regime"].iloc[-1]
    else:
        last_row = bt_opt.iloc[-1] if not bt_opt.empty else None
        current_regime = last_row.get("regime", None) if last_row is not None else None

    current_regime_label = map_regime_to_label(current_regime)

    if "date" in risk_score_df.columns:
        current_date = pd.to_datetime(risk_score_df["date"].iloc[-1])
    elif isinstance(risk_score_df.index, pd.DatetimeIndex):
        current_date = pd.to_datetime(risk_score_df.index[-1])
    else:
        raise RuntimeError("risk_score_df enthält keine 'date' Spalte und keinen DatetimeIndex.")

    # Use top-level get_investment_package and generate_investment_package
    try:
        prices_df, missing_total_prices, mapping = load_etf_universe_prices(start=DEFAULT_START_STR)
    except Exception:
        logging.getLogger(__name__).exception("load_etf_universe_prices schlug fehl")
        prices_df, missing_total_prices, mapping = pd.DataFrame(), [], {}

    if prices_df is None or (isinstance(prices_df, pd.DataFrame) and prices_df.empty) or prices_df.shape[1] == 0:
        st.error("Keine Preisdaten geladen. Prüfe ETF‑Ticker in risk_dashboard/config/etf_universe.yaml")
        st.stop()

    if missing_total_prices:
        st.warning("Folgende ETFs konnten nicht geladen werden und wurden im Backtest ignoriert: "
                + ", ".join(missing_total_prices))

    result = get_investment_package(
        risk_score_df,
        scenario_df,
        scenario_regimes,
        lambda r, s, rs: generate_investment_package(r, s, rs, ETF_UNIVERSES, prices_df)
    )

    st.subheader("Investment-Paket")
    st.write("Datum:", result.get("date"))
    st.write("Regime:", result.get("regime"))
    st.write("Szenario:", result.get("scenario"))
    st.write("Risiko-Score:", round(result.get("risk_score", float("nan")), 3))

    package = result.get("package", {})

    etf_raw = package.get("ETF", {})
    if isinstance(etf_raw, (set, list)):
        etf_list = list(etf_raw)
        etf = {t: 1.0/len(etf_list) for t in etf_list} if etf_list else {}
    elif isinstance(etf_raw, dict):
        etf = etf_raw
    else:
        etf = {}

    if etf:
        st.markdown("**ETF-Allokation:**")
        st.write(pd.DataFrame.from_dict(etf, orient="index", columns=["Gewicht"]))
    else:
        st.info("Keine ETF-Allokation im Paket vorhanden.")

    if "Equity Package" in package and isinstance(package["Equity Package"], dict):
        st.markdown("**Aktien/Equity Paket:**")
        st.write(pd.DataFrame.from_dict(package["Equity Package"], orient="index", columns=["Gewicht"]))

    # Plot Equity-Kurve for bt_opt
    try:
        fig_opt = px.line(
            bt_opt,
            x="date" if "date" in bt_opt.columns else bt_opt.index,
            y="equity",
            color="regime" if "regime" in bt_opt.columns else None,
            title=f"{opt_method} – Regime-gesteuertes Portfolio (Equity-Kurve)"
        )
        fig_opt.update_layout(yaxis_title="Equity (indexiert)", height=500)
        st.plotly_chart(fig_opt, width="stretch", key="fig_opt")
    except Exception:
        logging.getLogger(__name__).exception("Fehler beim Erstellen der Equity-Kurve")

    st.subheader(f"Performance-Kennzahlen ({opt_method}-Portfolio)")
    try:
        stats_opt = performance_stats(bt_opt)
        st.write(stats_opt)
    except Exception:
        logging.getLogger(__name__).exception("performance_stats schlug fehl")

    st.subheader(f"{opt_method}-Gewichte je Regime")
    for reg, info in opt_struct.items():
        st.markdown(f"### {reg}")
        weights = info.get("weights", {})
        fig_w = px.bar(
            x=list(weights.keys()),
            y=list(weights.values()),
            title=f"{opt_method} – Gewichte im {reg} Regime"
        )
        fig_w.update_layout(yaxis_title="Gewicht", height=350)
        st.plotly_chart(fig_w, width="stretch", key=f"weights_{reg}")

    # Outperformance: RP vs HRP
    st.markdown("---")
    st.subheader("Risk-Parity vs. HRP – Outperformance")

    bt_rp, rp_struct_tmp, missing_rp_tmp = backtest_regime_risk_parity(
        low_final,
        med_final,
        high_final,
        period="10y",
        scenario_df=scenario_df,
        scenario_regimes=scenario_regimes
    )
    st.write("DEBUG – RP Backtest Ergebnis (Head)2:", bt_rp.head() if hasattr(bt_rp, "head") else bt_rp)
    bt_hrp, hrp_struct_tmp, missing_hrp_tmp = backtest_regime_hrp(
        low_final,
        med_final,
        high_final,
        period="10y",
        scenario_df=scenario_df,
        scenario_regimes=scenario_regimes
    )

    if bt_rp is None or getattr(bt_rp, "empty", True) or bt_rp.shape[1] == 0:
        st.error("bt_rp enthält keine Daten oder keine Spalten – Backtest konnte nicht durchgeführt werden.")
        st.stop()

    if bt_hrp is None or getattr(bt_hrp, "empty", True) or bt_hrp.shape[1] == 0:
        st.error("bt_hrp enthält keine Daten oder keine Spalten – Backtest konnte nicht durchgeführt werden.")
        st.stop()

    #dates_rp = ensure_date_series(bt_rp)
    #dates_hrp = ensure_date_series(bt_hrp)
    
    
    # Direkt in app.py temporär einfügen (oder in einer separaten Debug‑Zelle)
    st.write("DEBUG bt_rp shape:", None if bt_rp is None else getattr(bt_rp, "shape", "no-shape"))
    st.write("DEBUG bt_rp columns:", None if bt_rp is None else list(bt_rp.columns))
    st.write("DEBUG bt_rp head:", None if bt_rp is None else bt_rp.head().to_dict())

    st.write("DEBUG bt_hrp shape:", None if bt_hrp is None else getattr(bt_hrp, "shape", "no-shape"))
    st.write("DEBUG bt_hrp columns:", None if bt_hrp is None else list(bt_hrp.columns))
    st.write("DEBUG bt_hrp head:", None if bt_hrp is None else bt_hrp.head().to_dict())

    # Prüfe auch die missing-Listen
    st.write("DEBUG missing_rp_tmp:", missing_rp_tmp)
    st.write("DEBUG missing_hrp_tmp:", missing_hrp_tmp)


    # Verwende die sichere Funktion
    dates_rp = _safe_ensure_date_series(bt_rp, label="bt_rp")
    dates_hrp = _safe_ensure_date_series(bt_hrp, label="bt_hrp")

    # Falls beide leer sind, abbrechen mit klarer Meldung
    if dates_rp.empty and dates_hrp.empty:
        st.error("Beide Backtests (Risk Parity und HRP) enthalten keine Datumsinformationen. Prüfe die Backtest-Funktionen und die geladenen ETF-Daten.")
        # Optional: Debug-Ausgabe für Entwickler
        st.write("DEBUG bt_rp head/shape:", getattr(bt_rp, "shape", None), getattr(bt_rp, "head", lambda: None)())
        st.write("DEBUG bt_hrp head/shape:", getattr(bt_hrp, "shape", None), getattr(bt_hrp, "head", lambda: None)())
        st.stop()

    base_dates = dates_rp if len(dates_rp) >= len(dates_hrp) else dates_hrp
    base_dates = base_dates.reset_index(drop=True)

    rp_equity = bt_rp["equity"].reset_index(drop=True) if "equity" in bt_rp.columns else pd.Series(dtype=float)
    hrp_equity = bt_hrp["equity"].reset_index(drop=True) if "equity" in bt_hrp.columns else pd.Series(dtype=float)

    min_len = min(len(base_dates), len(rp_equity), len(hrp_equity))

    df_compare = pd.DataFrame({
        "date": pd.to_datetime(base_dates.iloc[:min_len], errors="coerce"),
        "Risk Parity": rp_equity.iloc[:min_len].values,
        "HRP": hrp_equity.iloc[:min_len].values
    })

    df_compare["Outperformance"] = df_compare["HRP"] / df_compare["Risk Parity"]

    fig_out = px.line(
        df_compare,
        x="date",
        y="Outperformance",
        title="HRP Outperformance gegenüber Risk Parity"
    )
    fig_out.update_layout(height=500, yaxis_title="Outperformance (HRP / Risk Parity)")
    st.plotly_chart(fig_out, width="stretch", key="fig_out")

    st.markdown("---")
    st.subheader("Regime-Transitionsmatrix")

    trans = regime_transition_matrix()
    fig_trans = px.imshow(
        trans,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="Blues",
        title="Wahrscheinlichkeit von Regime-Wechseln"
    )
    st.plotly_chart(fig_trans, width="stretch")

    st.markdown("---")
    st.subheader("Regime-Heatmap (durchschnittliche Monatsrenditen)")

    heat = regime_heatmap_data(bt_opt)
    fig_heat = px.imshow(
        heat.T,
        text_auto=".2%",
        aspect="auto",
        color_continuous_scale="RdYlGn",
        title="Durchschnittliche Monatsrendite pro Regime"
    )
    st.plotly_chart(fig_heat, width="stretch")

    st.subheader("Sharpe-Heatmap pro Regime")

    sharpe_df = sharpe_per_regime(bt_opt)
    fig_sharpe = px.imshow(
        sharpe_df.T,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdYlGn",
        title="Sharpe Ratio pro Regime"
    )
    st.plotly_chart(fig_sharpe, width="stretch")

# ---------------------------------------------------------
# LEXIKON TAB
# ---------------------------------------------------------
with tab_lexikon:
    st.header("Makro-Lexikon")
    st.write("Ein Nachschlagewerk für alle wichtigen Begriffe, Modelle, Datenquellen und Investment-Zusammenhänge.")

    query = st.text_input("Begriff suchen:", key="lexikon_query")

    results = search_glossary(query)

    if not results and query:
        st.write("Keine Treffer gefunden.")
    elif not query:
        st.write("Bitte einen Suchbegriff eingeben (z.B. 'GDP', 'Inflation', 'Risk Score', 'Investieren').")
    else:
        for category, term, definition in results:
            st.subheader(category)
            with st.expander(term):
                st.write(definition)

    st.markdown('---')
    st.subheader('ETF Auswahl')
