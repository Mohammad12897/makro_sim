# risk_dashboard/app.py
# $env:PYTHONPATH="C:\Projects\makro_sim"
# $env:FRED_API_KEY = "5b75a1beb133f4e4aa6b8929ca39a762"
# setx FRED_API_KEY "5b75a1beb133f4e4aa6b8929ca39a762"
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
import os
import sys
import locale
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Any, Dict

import numpy as np
import plotly.graph_objects as go

print(">>> APP STARTED: TOP OF app.py", flush=True)

# Ensure project root is on sys.path so "scripts" package is importable
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

out_dir = project_root / "data" / "backtests"
out_dir.mkdir(parents=True, exist_ok=True)


# UTF-8 erzwingen (sicher)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
except Exception:
    pass

# Safety check before any heavy imports (optional)
AUTO_FIX = os.getenv("AUTO_FIX_PASTE_BLOCKS", "false").lower() in ("1", "true", "yes")

# Import minimal safety module if vorhanden
try:
    from risk_dashboard.core.safety import startup_safety_check
    startup_safety_check(project_root, auto_fix=AUTO_FIX)
except Exception:
    # If not present, continue silently
    pass

# Eigene Module (lokale Projektstruktur)
from risk_dashboard.core.data_loader import (
    load_raw_prices_for_universe,
    filter_valid_tickers
)
from risk_dashboard.core.ticker_cache import validate_ticker_with_cache
from risk_dashboard.data_cache import load_price_data_cached

# Streamlit optional importieren, mit sauberem Shim als Fallback
import os
import pandas as pd
import plotly.express as px

try:
    import streamlit as st

    # nach: import streamlit as st
    if "backtest_ran" not in st.session_state:
        st.session_state["backtest_ran"] = False

    def maybe_run_backtest(run_fn, *args, **kwargs):
        """
        Führt run_fn nur einmal pro Streamlit‑Session aus.
        Aufruf: maybe_run_backtest(run_backtest, params)
        """
        if not st.session_state["backtest_ran"]:
            st.session_state["backtest_ran"] = True
            return run_fn(*args, **kwargs)
        return None

except Exception:
    class _StreamlitShim:
        def write(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass
        def markdown(self, *args, **kwargs): pass
        def header(self, *args, **kwargs): pass
        def subheader(self, *args, **kwargs): pass
        def spinner(self, *args, **kwargs):
            class _Dummy:
                def __enter__(self): return None
                def __exit__(self, exc_type, exc, tb): return False
            return _Dummy()
        def columns(self, *args, **kwargs):
            # returns list of dummy column contexts
            return [self] * (len(args) if args else 1)
        def container(self, *args, **kwargs):
            return self
        def expander(self, *args, **kwargs):
            class _Exp:
                def __enter__(self): return None
                def __exit__(self, exc_type, exc, tb): return False
            return _Exp()
    st = _StreamlitShim()

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
    if df is None or df.empty:
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


# --- Docs / dynamische Seitenliste ---
docs_dir = project_root / "risk_dashboard" / "docs"
docs = sorted(docs_dir.glob("*.md"))
pages = {p.stem: str(p) for p in docs}  # key = filename without suffix, value = full path

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

# --- Layout ---
st.set_page_config(page_title="Risk Dashboard", layout="wide")
st.sidebar.title("Navigation")

# Sidebar Auswahl aus dynamischer pages‑Liste
choice = st.sidebar.selectbox("Seite wählen", list(pages.keys()))

# Topbar / Header
st.title("Risk Dashboard")
show_intro(pages[choice])  # kontextuelle Einführung oben auf jeder Seite

print(">>> BEFORE BACKTESTS", flush=True)

# Seiteninhalt
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

    st.subheader("ETF Vergleich")
    etf_list = st.multiselect(
        "ETFs auswählen",

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

    query = st.text_input("Begriff suchen:")

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
    # --- ETF Auswahl UI oben auf der Seite ---
    try:
        import logging
        from risk_dashboard.ui.etf_selection_ui import render_etf_selection_ui
        with st.container():
            render_etf_selection_ui()
    except Exception as _e:
        logging.getLogger(__name__).exception("Fehler beim Rendern der ETF Auswahl UI oben: %s", _e)