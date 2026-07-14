# risk_dashboard/ui/profiles_ui.py
"""
Streamlit UI for managing portfolio profiles (presets) with validation and analysis.
"""
from pathlib import Path
import sys
import traceback
from typing import Dict, Any, Tuple, Optional, List, Sequence
from io import StringIO
import requests
import plotly.graph_objects as go
import pandas as pd

from rich import region
import streamlit as st
import yaml
import tempfile, os, json
import logging, inspect, pathlib
 

from risk_dashboard.core.config import load_profiles, save_profile, load_etf_universe
from risk_dashboard.core.utils import extract_close_series, resolve_components, analyze_portfolio_components, normalize_ter_value
from risk_dashboard.core.backtest import run_all_etf_backtests, run_portfolio_backtest

from risk_dashboard.core.analysis import analyze_ticker
from risk_dashboard.core.weights import compute_abs_weights
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.holdings import load_ishares_holdings, etf_to_isin_map, load_holdings_with_fallback
from risk_dashboard.core.macro_pipeline import (
    detect_regime,
    select_etfs_for_regime,
    build_regime_portfolio,
    run_backtest,
    analyze_performance
)

from risk_dashboard.core.holdings import try_relaxed_holdings
from risk_dashboard.core.etf_tools import download_prices
from risk_dashboard.core.helpers import classify_etf

logger = logging.getLogger(__name__)


logger.debug("DEBUG: run_backtest from:", run_backtest.__module__)
os.makedirs("risk_dashboard/data", exist_ok=True)


# session state defaults (einmalig, ganz oben in profiles_ui.py)
if "new_ticker" not in st.session_state:
    st.session_state["new_ticker"] = ""
# optional: falls du weitere Keys nutzt
if "selected_etfs" not in st.session_state:
    st.session_state["selected_etfs"] = []
if "profile_selected" not in st.session_state:
    st.session_state["profile_selected"] = "<Neu>"

# mögliche Pfade (zuerst package/data, dann repo-root/data)
CSV_CANDIDATES = [
    Path(__file__).parents[1] / "data" / "attribut-warum-wichtig-12.csv",
    Path(__file__).parents[2] / "data" / "attribut-warum-wichtig-12.csv",
]

BASE_DIR = Path(__file__).resolve().parents[1] # risk_dashboard
LEX_PATH = BASE_DIR / "docs" / "lexikon.md"


holdings_dir = BASE_DIR / "data" / "holdings"
price_path = BASE_DIR / "data" / "price_data.csv"
macro_path = BASE_DIR / "data" / "macro_df.csv"
ETF_UNIVERSE_PATH = BASE_DIR / "data" / "etf_universe.yaml"


TOOLTIPS = {
    "profile_name": "Name des Profils, z. B. Conservative, Balanced, Aggressive.",
    "category": "Basis-Risikokategorie; fällt empfohlene Standardwerte vor.",
    "equity_pct": "Anteil Aktien am Portfolio in Prozent.",
    "bond_pct": "Anteil Anleihen am Portfolio in Prozent.",
    "cash_pct": "Liquiditätsreserve in Prozent.",
    "target_annual_return_pct": "Erwartete durchschnittliche Jahresrendite (Schätzwert).",
    "max_drawdown_pct": "Maximal tolerierter Verlust vom Peak (z. B. 20 für 20%).",
    "rebalance": "Wie oft automatisch umgeschichtet werden soll.",
    "allowed_instruments": "Erlaubte Asset-Klassen oder ETFs (Keys aus dem ETF-Universe).",
    "notes": "Kurze Beschreibung des Profils.",
}

vol_map = {"equity": 15, "bond": 5, "cash": 1}

CATEGORY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Low": {"equity_pct": 10, "bond_pct": 80, "cash_pct": 10, "target_annual_return_pct": 3.0, "max_drawdown_pct": 8, "rebalance": "quarterly"},
    "Medium": {"equity_pct": 45, "bond_pct": 45, "cash_pct": 10, "target_annual_return_pct": 6.0, "max_drawdown_pct": 20, "rebalance": "monthly"},
    "High": {"equity_pct": 85, "bond_pct": 10, "cash_pct": 5, "target_annual_return_pct": 10.0, "max_drawdown_pct": 35, "rebalance": "monthly"},
}


ETF_INFO = {
    "iShares": {
        "anbieter": "BlackRock (UK/US)",
        "region": "Global / US / UK",
        "replikation": "Physisch",
        "ter": "0.07 – 0.20 %",
    },
    "Vanguard": {
        "anbieter": "Vanguard Group (US)",
        "region": "Global / US",
        "replikation": "Physisch",
        "ter": "0.07 – 0.22 %",
    },
    "Xtrackers": {
        "anbieter": "DWS (DE)",
        "region": "Europa / Deutschland",
        "replikation": "Physisch / Synthetisch",
        "ter": "0.09 – 0.25 %",
    },
    "Amundi": {
        "anbieter": "Amundi (FR)",
        "region": "Europa / Global",
        "replikation": "Physisch",
        "ter": "0.15 – 0.30 %",
    },
    "Cash": {
        "anbieter": "Barbestand",
        "region": "Keine Region",
        "replikation": "Keine",
        "ter": "–",
    },
    "Unbekannt": {
        "anbieter": "Unbekannt",
        "region": "–",
        "replikation": "–",
        "ter": "–",
    },
}

ETF_LOGOS = {
    "iShares": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Ishares_logo.svg",
    "Vanguard": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Vanguard_logo.svg",
    "Xtrackers": "https://upload.wikimedia.org/wikipedia/commons/4/4e/DWS_Group_logo.svg",
    "Amundi": "https://upload.wikimedia.org/wikipedia/commons/8/8e/Amundi_logo.svg",
    "Cash": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Cash_icon.png",
    "Unbekannt": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Question_mark.svg",
}

REPLICATION_TOOLTIP = {
    "physical": "Physisch replizierend: ETF hält die echten Aktien.",
    "synthetic": "Synthetisch replizierend: ETF nutzt Swaps statt echter Aktien.",
    None: "Keine Angaben verfügbar."
}

def get_shared(name):
    # bevorzugt session_state, dann modul-globals, sonst None
    val = st.session_state.get(name)
    if val is not None:
        return val
    val = globals().get(name)
    if val is not None:
        return val
    return None


def load_etf_yaml():
    try:
        if ETF_UNIVERSE_PATH.exists():
            with open(ETF_UNIVERSE_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        st.warning("Fehler beim Laden von ETF YAML; benutze leeres Mapping.")
    return {}

def load_macro_data():
    # Dummy-Daten bis echte Makrodaten angebunden sind
    df = pd.DataFrame({
        "inflation": [2.1, 2.4, 3.0, 3.4],
        "yield_curve": [0.5, 0.2, -0.1, -0.3],
        "growth": [1.5, 1.2, 0.4, -0.2]
    })
    return df

def load_portfolio_from_ui_or_disk(session_key="portfolio_df"):
    # 1) Versuche session_state
    df = st.session_state.get(session_key)
    logger.debug("session_state keys: %s", list(st.session_state.keys()))
    logger.debug("portfolio_df present in session: %s", session_key in st.session_state)

    # 2) File uploader (UI) — eindeutiger key
    uploaded = st.file_uploader(
        "Portfolio CSV (ticker, quantity, price, market_value optional)",
        type=["csv"],
        key=f"portfolio_uploader_{session_key}"
    )
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            logger.debug("Loaded portfolio from uploader shape=%s columns=%s", getattr(df, "shape", None), list(df.columns))
            st.session_state[session_key] = df
            return df
        except Exception:
            logger.exception("Failed to parse uploaded portfolio CSV")
            st.error("Fehler beim Einlesen der hochgeladenen CSV.")
            return pd.DataFrame()

    # 3) Fallback: Datei auf Disk
    disk_path = Path("risk_dashboard/data/portfolio.csv")  # oder holdings/portfolio.csv
    logger.debug("Trying to load CSV from %s exists=%s", disk_path, disk_path.exists())
    if disk_path.exists():
        try:
            df = pd.read_csv(disk_path)
            st.session_state[session_key] = df
            logger.debug("Loaded portfolio from disk shape=%s", df.shape)
            return df
        except Exception:
            logger.exception("Failed to read portfolio CSV from disk")
            st.error("Fehler beim Lesen der Portfolio‑CSV von der Festplatte.")
            return pd.DataFrame()

    # 4) Kein Portfolio gefunden -> leeres DataFrame
    logger.debug("No portfolio found; returning empty DataFrame")
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_from_api(ticker: str, api_key: str) -> pd.DataFrame:
    url = "https://apidata.fin2dev.com/v1/etfholdings"
    params = {"key": api_key, "ticker": ticker}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("result", {}).get("holdings", [])
    return pd.DataFrame([{"ticker":h["ticker"], "weight_in_etf": float(h["percent_value"])/100} for h in data])

@st.cache_data(ttl=3600)
def fetch_from_provider_csv(ticker: str) -> pd.DataFrame:
    # Beispiel: iShares/Vanguard bieten CSV-Links; hier musst du die konkrete URL-Logik implementieren
    csv_url = f"https://www.ishares.com/.../holdings/{ticker}.csv"  # placeholder
    r = requests.get(csv_url, timeout=10)
    r.raise_for_status()
    df = pd.read_csv(pd.compat.StringIO(r.text))
    # Debug: zeigt dir, was wirklich eingelesen wurde
    logger.debug(
        "read df shape=%s columns=%s sample=%s",
        getattr(df, 'shape', None),
        list(df.columns),
        df.head().to_dict(orient='records')[:3]
    )

    # mappe provider-spalten auf weight_in_etf
    return pd.DataFrame({"ticker": df["ticker"], "weight_in_etf": df["weight"]/100.0})

def get_etf_holdings(ticker: str) -> pd.DataFrame:
    API_KEY = st.secrets.get("ETF_API_KEY")  # set in Streamlit secrets
    # 1) Try official API
    try:
        if API_KEY:
            return fetch_from_api(ticker, API_KEY)
    except Exception:
        pass
    # 2) Try provider CSV
    try:
        return fetch_from_provider_csv(ticker)
    except Exception:
        pass
    # 3) Fallback: local scraper library (requires pip install etf_scraper)
    try:
        from etf_scraper import ETFScraper
        s = ETFScraper()
        hdf = s.query_holdings(ticker)
        return pd.DataFrame({"ticker": hdf["ticker"], "weight_in_etf": hdf["weight"]/100.0})
    except Exception:
        st.warning(f"Holdings für {ticker} konnten nicht automatisch geladen werden. Bitte CSV hochladen.")
        return pd.DataFrame()

# Hilfsfunktionen
def compute_portfolio_value(df: pd.DataFrame) -> float:
    if "market_value" not in df.columns:
        df["market_value"] = df["quantity"].fillna(0) * df["price"].fillna(0)
    return float(df["market_value"].sum())

def compute_etf_breakdown(etf_market_value: float, holdings_df: pd.DataFrame, portfolio_value: float) -> pd.DataFrame:
    h = holdings_df.copy()
    h["abs_weight_in_portfolio"] = h["weight_in_etf"] * (etf_market_value / portfolio_value) if portfolio_value > 0 else 0.0
    return h

def load_etf_holdings(uploaded_file):
    # read
    df = pd.read_csv(uploaded_file)

    # Debug: zeigt dir, was wirklich eingelesen wurde
    logger.debug(
        "read df shape=%s columns=%s sample=%s",
        getattr(df, 'shape', None),
        list(df.columns),
        df.head().to_dict(orient='records')[:3]
    )
    # normalize column names
    df.columns = df.columns.str.strip().str.lower()
    # mögliche Varianten prüfen
    if "weight_in_etf" in df.columns:
        col = "weight_in_etf"
    elif "weight" in df.columns:
        col = "weight"
    elif "weight_in_etf%" in df.columns:
        col = "weight_in_etf%"
    else:
        # keine Gewichtsspalte: Fallback oder Fehlerbehandlung
        st.warning("CSV enthält keine Spalte 'weight_in_etf' oder 'weight'. Demo‑Werte werden verwendet.")
        df["weight_in_etf"] = 0.0
        return df

    # Konvertieren und normalisieren (z. B. Prozentangaben wie '30%' behandeln)
    def to_float(x):
        try:
            if isinstance(x, str) and x.strip().endswith("%"):
                return float(x.strip().rstrip("%")) / 100.0
            return float(x)
        except Exception:
            return 0.0

    df["weight_in_etf"] = df[col].apply(to_float)
    return df

def normalize_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Spalten säubern
    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '')
    # ticker prüfen
    if "ticker" not in df.columns:
        raise ValueError("CSV muss eine 'ticker' Spalte enthalten.")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    # mögliche Gewichtsspalten erkennen
    if "weight_in_etf" in df.columns:
        src = "weight_in_etf"
    elif "weight" in df.columns:
        src = "weight"
    elif "weight_in_etf%" in df.columns:
        src = "weight_in_etf%"
    else:
        # keine Gewichtsspalte: setze 0.0 als Fallback
        df["weight_in_etf"] = 0.0
        return df

    def to_float(x):
        if pd.isna(x):
            return 0.0
        s = str(x).strip()
        if s.endswith("%"):
            try:
                return float(s.rstrip("%")) / 100.0
            except Exception:
                return 0.0
        try:
            return float(s)
        except Exception:
            return 0.0

    df["weight_in_etf"] = df[src].apply(to_float)
    return df

def render_etf_tab(session_state):
    # --- Dashboard‑Dokumentation / Gebrauchsanweisung ---
    with st.expander("📘 Dashboard‑Beschreibung und Gebrauchsanweisung"):
        DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "dashboard_guide.md"
        if DOC_PATH.exists():
            st.markdown(DOC_PATH.read_text(encoding="utf-8"))
        else:
            st.write("Dokumentation nicht gefunden. Bitte lege docs/dashboard_guide.md an.")

    st.header("ETF vs Aktie — Absolute Gewichte (Live)")
    with st.expander("Kurzhilfe"):
        st.markdown(
            "ETF = Korb aus Wertpapieren (eigener Ticker). "
            "Absolute Gewicht = Marktwert Position / Gesamtportfolio. "
            "Bei ETFs: ETF_abs * weight_in_etf = absolutes Gewicht der Underlyings."
        )
    st.markdown("---")

    # --- Status-Legende ---
    st.markdown("""
    ### 🔍 Status-Legende
    🟢 **iShares (UK/US)** – echte Holdings verfügbar  
    🟡 **Vanguard / Amundi / Xtrackers / EU / US / UK** – keine iShares-CSV, Demo-Holdings  
    🔴 **Cash / Nicht-ETF** – keine Holdings  
    ---
    """)


    # 1) Portfolio Input
    df = load_portfolio_from_ui_or_disk()
    # --- Validierung: mindestens 'ticker' vorhanden und market_value berechnen ---
    required = {"ticker"}
    if not df.empty:
        if not required.issubset(set(df.columns)):
            st.error("CSV muss mindestens Spalte 'ticker' enthalten.")
            df = pd.DataFrame()  # Abbruch / überspringen weiterer Schritte
        else:
            # market_value berechnen, falls fehlt
            if "market_value" not in df.columns:
                qty = df["quantity"].astype(float).fillna(0.0) if "quantity" in df.columns else pd.Series(0.0, index=df.index)
                price = df["price"].astype(float).fillna(0.0) if "price" in df.columns else pd.Series(0.0, index=df.index)
                df["market_value"] = qty * price
                logger.debug("Computed market_value for portfolio sample=%s", df[["ticker","market_value"]].head().to_dict(orient="records"))
            st.session_state["portfolio_df"] = df

    # sichere Initialisierung aus session_state
    df = st.session_state.get("portfolio_df", pd.DataFrame())

    # sichere Berechnung market_value nur wenn df nicht leer ist
    if not df.empty:
        st.dataframe(df)
        # sichere Series für quantity und price (falls Spalte fehlt, ersetze durch 0er-Serie)
        if "quantity" in df.columns:
            qty = df["quantity"].astype(float).fillna(0.0)
        else:
            qty = pd.Series(0.0, index=df.index)

        if "price" in df.columns:
            price = df["price"].astype(float).fillna(0.0)
        else:
            price = pd.Series(0.0, index=df.index)

        df["market_value"] = qty * price

        # optional: schreibe das aktualisierte df zurück in session_state
        st.session_state["portfolio_df"] = df

    auto_portfolio_value = compute_portfolio_value(df) if not df.empty else 0.0
    portfolio_value = st.number_input("Gesamtportfolio (leer = Summe der Marktwerte)", value=float(auto_portfolio_value), format="%.2f")

    # 2) Auswahl ETFs aus Portfolio
    tickers = df["ticker"].astype(str).str.upper().unique().tolist() if not df.empty else []
    selected_etfs = st.multiselect("Aus Portfolio wähle ETF(s) zur Aufschlüsselung", options=tickers)

    # 3) Holdings pro ETF
    holdings_map: Dict[str, pd.DataFrame] = {}

    holdings_dir.mkdir(parents=True, exist_ok=True)

    etf_to_isin_map = get_shared("etf_to_isin_map")
    if etf_to_isin_map is None:
        etf_to_isin_map = globals().get("etf_to_isin_map", {})


    # Debug: Pfade in UI
    st.write("DEBUG price_path:", price_path)
    st.write("DEBUG macro_path:", macro_path)
    st.write("price_path exists:", price_path.exists())
    st.write("macro_path exists:", macro_path.exists())

    # Sicheres Lesen von shared DataFrames
    price_data = get_shared("price_data")
    macro_df = get_shared("macro_df")

    # Falls price_data noch None ist und etf_universe vorhanden ist, versuche Loader (falls nötig)
    etf_universe, universe_warnings = load_etf_universe()
    if price_data is None:
        try:
            price_data = load_price_data(etf_universe)
            st.session_state["price_data"] = price_data
        except Exception as e:
            st.error(f"Fehler in load_price_data(): {e}")
            price_data = None

    # Falls macro_df noch None, versuche Loader oder CSV-Fallback
    if macro_df is None:
        try:
            macro_df = load_macro_data()
            st.session_state["macro_df"] = macro_df
        except Exception:
            # Verwende einen anderen lokalen Namen, damit die modulweite macro_path nicht überschrieben wird
            macro_csv_path = BASE_DIR / "data" / "macro_df.csv"
            if macro_csv_path.exists():
                try:
                    macro_df = pd.read_csv(macro_csv_path, index_col=0, parse_dates=True)

                    # Debug: zeigt dir, was wirklich eingelesen wurde
                    logger.debug(
                        "read df shape=%s columns=%s sample=%s",
                        getattr(macro_df, 'shape', None),
                        list(macro_df.columns),
                        macro_df.head().to_dict(orient='records')[:3]
                    )
                    st.session_state["macro_df"] = macro_df
                except Exception as e:
                    st.error("Fehler beim Laden von macro_df.csv: " + str(e))
                    macro_df = None


    # UI‑Warnungen, falls Daten fehlen
    if price_data is None:
        st.warning("Preisdaten (price_data) fehlen. Backtest wird beim Klick geprüft.")
    if macro_df is None:
        st.warning("Makrodaten (macro_df) fehlen. Backtest wird beim Klick geprüft.")


    # --- Hilfsfunktionen / Konstanten (einmalig definieren) ---
    def detect_region(etf: str) -> str:
        if etf.endswith(".L"):
            return "UK"
        if etf.endswith(".DE"):
            return "Deutschland"
        if etf.endswith(".US"):
            return "USA"
        if etf.endswith(".FR"):
            return "Frankreich"
        return "Global"

    # ETF_LOGOS, ETF_INFO, REPLICATION_TOOLTIP sollten oben definiert sein (wie zuvor besprochen)

    # Lade YAML einmal (nicht in der Schleife)
    ETF_YAML = load_etf_yaml()  # erwartet: Funktion load_etf_yaml() existiert

    # Stelle sicher, dass diese Variablen/Objekte existieren:
    # holdings_dir: Path zu holdings CSVs
    # etf_to_isin_map: dict mapping etf->isin
    # price_data, macro_df: müssen vor dem Button/Backtest definiert sein
    # normalize_holdings_df, load_holdings_with_fallback, load_ishares_holdings existieren idealerweise

    for etf in selected_etfs:
        category, tooltip = classify_etf(etf)

        # Region automatisch erkennen
        region = detect_region(etf)

        # Logo anzeigen
        logo_url = ETF_LOGOS.get(category, ETF_LOGOS["Unbekannt"])
        st.image(logo_url, width=80)

        # ETF‑Info‑Panel
        info = ETF_INFO.get(category, ETF_INFO["Unbekannt"])

        yaml_info = ETF_YAML.get(etf, {})
        ter = yaml_info.get("ter", "–")
        replication = yaml_info.get("replication", None)
        region_yaml = yaml_info.get("region", None)
        replication_text = REPLICATION_TOOLTIP.get(replication, "Keine Angaben verfügbar.")

        st.markdown(
            f"""
            <div style="border:1px solid #ccc; border-radius:8px; padding:10px; background-color:#f9f9f9;">
                <b>Anbieter:</b> {info['anbieter']}<br>
                <b>Region:</b> {region_yaml or region}<br>
                <b>Replikation:</b> {replication or info['replikation']}<br>
                <small>{replication_text}</small><br>
                <b>TER:</b> {ter}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- farbige Statusanzeige mit Tooltip ---
        color_map = {
            "iShares": "#00A65A",
            "Vanguard": "#B00000",
            "Xtrackers": "#004C97",
            "Amundi": "#0072CE",
            "Cash": "#808080",
            "Unbekannt": "#999999",
        }

        color = color_map.get(category, "#999999")
        st.markdown(f"<span style='color:{color}; font-weight:bold;'>■</span> **{etf} — Kategorie: {category}**", unsafe_allow_html=True)
        st.caption(f"ℹ️ {tooltip}")

        st.markdown(f"**Holdings für {etf}**")

        hdf = pd.DataFrame()
        df_key = f"holdings_{etf}"

        # Checkboxen
        use_demo = st.checkbox(f"Demo‑Holdings für {etf} anzeigen", key=f"demo_{etf}")
        use_ishares = st.checkbox(f"Echte iShares‑Holdings für {etf} laden", key=f"ishares_{etf}")

        uploaded_h = st.file_uploader(f"Holdings CSV für {etf} (ticker, weight_in_etf)", key=f"h_{etf}")

        # 1) CSV Upload
        if uploaded_h is not None:
            try:
                hdf = pd.read_csv(uploaded_h)
                # Debug: zeigt dir, was wirklich eingelesen wurde
                logger.debug(
                    "read df shape=%s columns=%s sample=%s",
                    getattr(hdf, 'shape', None),
                    list(hdf.columns),
                    hdf.head().to_dict(orient='records')[:3]
                )
                # sichere Funktionsermittlung (einmalig)
                normalize_fn = globals().get("normalize_holdings_df")
                if callable(normalize_fn):
                    try:
                        hdf = normalize_fn(hdf)
                    except Exception as e:
                        st.warning(f"normalize_holdings_df schlug fehl: {e} — verwende unbearbeitete CSV.")
                # session_state setzen
                st.session_state[df_key] = hdf

                # speichern
                save_path = holdings_dir / f"{etf}.csv"
                save_path.parent.mkdir(parents=True, exist_ok=True)
                hdf.to_csv(save_path, index=False)
                st.success("Holdings CSV erfolgreich geladen.")
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Holdings‑CSV für {etf}: {e}")

        # 2) iShares Internet‑Holdings (nur wenn Checkbox gesetzt)
        elif use_ishares:
            # definiere isin sicher
            isin = None
            if etf_to_isin_map and etf in etf_to_isin_map:
                isin = etf_to_isin_map[etf]

            logger.debug("holdings_dir (resolved) = %s", holdings_dir.resolve())
            logger.debug("etf variable = %r", etf)
            candidates = sorted(holdings_dir.glob(f"{etf}.*"))
            logger.debug("candidates for %s = %s", etf, [str(p) for p in candidates])

            # innerhalb: for etf in selected_etfs:
            st.markdown(f"**Holdings für {etf}**")
            df_key = f"holdings_{etf}"
            path_to_csv = holdings_dir / f"{etf}.csv"

            # 1) Versuche relaxed fallback (einfaches ticker,weight_in_etf CSV)
            ok, res = try_relaxed_holdings(path_to_csv)
            if ok:
                hdf = res
                logger.debug("Using relaxed holdings for %s (accepted)", etf)
                st.session_state[df_key] = hdf
                path_to_csv.parent.mkdir(parents=True, exist_ok=True)
                hdf.to_csv(path_to_csv, index=False)
                st.success(f"Holdings für {etf} aus lokaler CSV geladen (relaxed fallback).")
                # nur diese Iteration beenden, nächste ETF verarbeiten
                continue

            # 2) relaxed nicht verwendet -> bestehende Logik ausführen
            hdf = load_holdings_with_fallback(etf, category, isin, df_key, holdings_dir)

            # 3) iShares / Demo Logik (nur hier, nicht vorher)
            if category == "iShares" and isin:
                try:
                    hdf = load_ishares_holdings(isin)
                    hdf = normalize_holdings_df(hdf) if callable(normalize_holdings_df) else hdf
                    hdf.to_csv(path_to_csv, index=False)
                    st.session_state[df_key] = hdf
                    st.success(f"Echte iShares‑Holdings geladen und gespeichert unter: {path_to_csv}")
                except Exception:
                    st.warning(f"⚠️ Keine gültige iShares‑CSV für {etf} gefunden. Demo‑Holdings werden verwendet.")
                    hdf = pd.DataFrame([
                        {"ticker": "AAPL", "weight_in_etf": 0.30},
                        {"ticker": "MSFT", "weight_in_etf": 0.30},
                        {"ticker": "NVDA", "weight_in_etf": 0.20},
                        {"ticker": "AMZN", "weight_in_etf": 0.20},
                    ])
                    st.caption("Demo‑Holdings (automatischer Fallback).")
                    st.session_state[df_key] = hdf
            else:
                st.warning(f"{etf} ist kein iShares‑ETF oder ISIN fehlt — Demo‑Holdings werden verwendet.")
                hdf = pd.DataFrame([
                    {"ticker": "AAPL", "weight_in_etf": 0.30},
                    {"ticker": "MSFT", "weight_in_etf": 0.30},
                    {"ticker": "NVDA", "weight_in_etf": 0.20},
                    {"ticker": "AMZN", "weight_in_etf": 0.20},
                ])
                st.caption("Demo‑Holdings (automatischer Fallback).")
                st.session_state[df_key] = hdf


                logger.warning("Keine gültige iShares‑CSV für %s gefunden. Demo‑Holdings werden verwendet.", etf)
                logger.debug("Stacktrace for demo-fallback:\n%s", "".join(traceback.format_stack()))


        # 3) Session oder Disk
        else:
            if df_key in st.session_state:
                hdf = st.session_state[df_key]
            else:
                disk_file = holdings_dir / f"{etf}.csv"
                if disk_file.exists():
                    try:
                        hdf = pd.read_csv(disk_file)
                        # Debug: zeigt dir, was wirklich eingelesen wurde
                        logger.debug(
                            "read df shape=%s columns=%s sample=%s",
                            getattr(hdf, 'shape', None),
                            list(hdf.columns),
                            df.head().to_dict(orient='records')[:3]
                        )
                        hdf = normalize_holdings_df(hdf) if callable(normalize_holdings_df) else hdf
                        st.session_state[df_key] = hdf
                    except Exception as e:
                        st.error(f"Fehler beim Laden der gespeicherten Holdings für {etf}: {e}")

        # 4) Demo fallback (wenn explizit angefordert oder immer noch leer)
        if (hdf is None or hdf.empty) and use_demo:
            hdf = pd.DataFrame([
                {"ticker": "AAPL", "weight_in_etf": 0.30},
                {"ticker": "MSFT", "weight_in_etf": 0.30},
                {"ticker": "NVDA", "weight_in_etf": 0.20},
                {"ticker": "AMZN", "weight_in_etf": 0.20},
            ])
            st.caption("Demo‑Holdings (nur Testzwecke).")
            st.session_state[df_key] = hdf

        # Anzeige
        if hdf is not None and not hdf.empty:
            st.dataframe(hdf.head(10))
        else:
            st.info("Keine Holdings geladen. Lade eine CSV hoch, aktiviere iShares oder Demo.")

        holdings_map[etf] = hdf.copy() if (isinstance(hdf, pd.DataFrame) and not hdf.empty) else pd.DataFrame()



    # Console logs (für dev)
    logger.debug("DEBUG: sys.path (first 10):", sys.path[:10])
    
    price_data = get_shared("price_data")
    macro_df = get_shared("macro_df")

    # Konsole / Streamlit UI ausgeben (temporär)
    #st.write("DEBUG session_state keys:", list(st.session_state.keys()))
    #st.write("DEBUG price_data in session_state:", "price_data" in st.session_state)

    
    # Fehlerhinweise (falls Daten fehlen)
    # UI‑Warnungen
    if price_data is None:
        st.warning("Preisdaten (price_data) fehlen. Backtest wird beim Klick geprüft.")
    if macro_df is None:
        st.warning("Makrodaten (macro_df) fehlen. Backtest wird beim Klick geprüft.")

    # Button immer anzeigen (ein Key, nur einmal im Repo)
    if st.button("Berechnen", key="btn_etf_calculate"):

        pd_shared = get_shared("price_data")
        md_shared = get_shared("macro_df")

        if pd_shared is None:
            st.error("Preisdaten (price_data) sind nicht definiert. Backtest abgebrochen.")
            return

        if md_shared is None:
            st.error("Makrodaten (macro_df) sind nicht definiert. Backtest abgebrochen.")
            return

        try:
            out = run_all_etf_backtests(
                selected_etfs=selected_etfs,
                holdings_dir=holdings_dir,
                etf_to_isin_map=etf_to_isin_map,
                price_data=pd_shared,
                macro_df=md_shared,
                backtest_dir=Path("risk_dashboard/data/backtests"),
                portfolio_value=st.session_state.get("portfolio_value", 100000.0),
            )
        except Exception as e:
            st.error(f"Backtest fehlgeschlagen: {e}")
            logger.exception("Backtest failed: %s", e)
            return

        st.success("Backtests abgeschlossen.")
        st.json(out)
            
    st.markdown("---")


def load_attribute_table_try(paths):
    for p in paths:
        try:
            if p.exists():
                return pd.read_csv(p, encoding="utf-8-sig")
        except Exception as e:
            # loggen, aber weitermachen zum nächsten Pfad
            import logging
            logging.getLogger(__name__).warning("Fehler beim Lesen %s: %s", p, e)
    # fallback: eingebetteter Default-CSV (klein)
    CSV_TEXT = """Attribut,Warum wichtig
Preisverlauf / Historie,"Basis für Rendite, Volatilität, Drawdown"
Annualisierte Rendite,Vergleichbarkeit über Zeiträume
Volatilität (Std. Abw.),Risiko‑Maß
Sharpe Ratio,Rendite pro Risikoeinheit
Max Drawdown,Worst‑case Verlust
Korrelation mit Portfolio,Diversifikationswirkung
Holdings / Sektorgewicht,Was steckt im ETF? Konzentrationsrisiko
TER / Kostenquote,Laufende Kosten reduzieren Rendite
AUM / Liquidität,"Handelbarkeit, Tracking‑Stabilität"
Dividendenrendite,Ertragskomponente
Tracking Error,Für ETFs: Abweichung vom Index
Währung / Domizil / Steuer,Wechselkurs‑ und Steuerimplikationen
"""
    return pd.read_csv(StringIO(CSV_TEXT))

# Einmaliges Laden
attr_df = load_attribute_table_try(CSV_CANDIDATES)
attr_map = dict(zip(attr_df["Attribut"], attr_df["Warum wichtig"]))

used = None
metrics = {}
prices_multi = None

label_map = {
    "annual_return": "Annualisierte Rendite",
    "annual_vol": "Volatilität (Std. Abw.)",
    "sharpe": "Sharpe Ratio",
    "max_drawdown": "Max Drawdown"
}

def normalize_weights(equity: float, bond: float, cash: float) -> Tuple[float, float, float]:
    total = equity + bond + cash
    if total == 0:
        return equity, bond, cash
    return (round(equity / total * 100, 2), round(bond / total * 100, 2), round(cash / total * 100, 2))

def _init_session_state_defaults() -> None:
    if "selected_etfs" not in st.session_state:
        st.session_state.selected_etfs = []
    if "profile_selected" not in st.session_state:
        st.session_state.profile_selected = "<Neu>"
        

def detect_risk_category(eq: float, bd: float, cs: float) -> str:
    vol_equity = vol_map["equity"]
    vol_bonds = vol_map["bond"]
    vol_cash = vol_map["cash"]
    portfolio_vol = (eq / 100.0) * vol_equity + (bd / 100.0) * vol_bonds + (cs / 100.0) * vol_cash
    if portfolio_vol < 6:
        return "Low"
    elif portfolio_vol < 12:
        return "Medium"
    else:
        return "High"

def apply_preset(keys: list, etf_universe: dict):
    missing = [k for k in keys if k not in etf_universe]
    if missing:
        st.warning(f"Preset enthält nicht verfügbare ETFs: {', '.join(missing)}")
    st.session_state.selected_etfs = [k for k in keys if k in etf_universe]

# in risk_dashboard/ui/profiles_ui.py: ersetze die alte load_price_data durch diese Version
def load_price_data(etf_universe, *args, **kwargs):
    """
    Accepts either:
      - a dict mapping id -> {"ticker": "...", ...}
      - a list of ticker strings
    Returns a DataFrame of price series with tickers as columns.
    """
    # Accept list input and convert to expected dict format
    if isinstance(etf_universe, list):
        etf_universe = {t: {"ticker": t} for t in etf_universe}

    # Defensive: ensure values have 'ticker'
    tickers = []
    for v in (etf_universe.values() if isinstance(etf_universe, dict) else []):
        if isinstance(v, dict) and "ticker" in v:
            tickers.append(v["ticker"])
        else:
            # skip malformed entries
            continue

    # Fallback: if no tickers, try to interpret keys as tickers
    if not tickers and isinstance(etf_universe, dict):
        tickers = [k for k in etf_universe.keys()]

    # final normalization
    tickers = [str(t).strip().upper() for t in tickers if t]

    # original behavior: download_prices / download_prices wrapper
    prices = download_prices(tickers, start="2010-01-01")
    return prices



def detect_historical_regimes(
    macro_df: Optional[pd.DataFrame],
    required_cols: Sequence[str] = ("inflation", "gdp", "volatility"),
    defaults: dict = None,
    inflation_threshold: float = 3.0,
) -> pd.Series:
    """
    Ermittelt historische Regime aus macro_df und gibt eine pd.Series mit Regime-Labels zurück.
    - macro_df: DataFrame mit DatetimeIndex und Makrovariablen als Spalten (kann None sein).
    - required_cols: erwartete Spalten, die ggf. mit Defaults ergänzt werden.
    - defaults: dict mit Default-Werten für fehlende Spalten (falls None -> 0.0).
    - inflation_threshold: Beispiel-Schwelle für 'high_inflation'.
    """

    # Schutz gegen None
    if macro_df is None:
        # leere Series mit DatetimeIndex nicht möglich ohne Index; gib leere Series zurück
        logger.debug("WARN: detect_historical_regimes called with macro_df=None -> returning empty Series")
        return pd.Series(dtype="object")

    # Sicherstellen, dass Index ein DatetimeIndex ist
    if not isinstance(macro_df.index, pd.DatetimeIndex):
        try:
            macro_df = macro_df.copy()
            macro_df.index = pd.to_datetime(macro_df.index)
            logger.debug("INFO: macro_df.index converted to DatetimeIndex")
        except Exception:
            logger.debug("WARN: could not convert macro_df.index to DatetimeIndex; proceeding with original index")

    # Defaults setzen
    if defaults is None:
        defaults = {}
    for col in required_cols:
        if col not in macro_df.columns:
            default_value = defaults.get(col, 0.0)
            logger.debug(f"WARN: macro_df missing '{col}' column; filling with {default_value}")
            macro_df[col] = default_value

    # Beispiel-Logik: einfache Regime-Klassifikation
    regimes = []
    for _, row in macro_df.iterrows():
        # sichere Zugriffe mit .get (falls später weitere Keys fehlen)
        infl = row.get("inflation", defaults.get("inflation", 0.0))
        gdp = row.get("gdp", defaults.get("gdp", 0.0))
        vol = row.get("volatility", defaults.get("volatility", 0.0))

        # einfache Regeln (anpassbar)
        if pd.isna(infl):
            infl = defaults.get("inflation", 0.0)
        if infl > inflation_threshold:
            regimes.append("high_inflation")
        elif vol > 0.2:  # Beispiel: hohe Volatilität
            regimes.append("high_volatility")
        elif gdp < 0:
            regimes.append("recession")
        else:
            regimes.append("normal")

    return pd.Series(regimes, index=macro_df.index, name="regime")


def profile_form_ui() -> None:
    _init_session_state_defaults()

    # Session state defaults (einmalig)
    if "new_ticker" not in st.session_state:
        st.session_state["new_ticker"] = ""
    # Keys für Analyseergebnisse
    if "analysis_used" not in st.session_state:
        st.session_state["analysis_used"] = None
    if "analysis_metrics" not in st.session_state:
        st.session_state["analysis_metrics"] = {}
    if "analysis_prices_multi" not in st.session_state:
        st.session_state["analysis_prices_multi"] = None
    if "analysis_close_series" not in st.session_state:
        st.session_state["analysis_close_series"] = None


    st.header("Portfolio Profile")

    cfg = load_profiles()
    profiles = cfg.get("profiles", {}) if isinstance(cfg, dict) else {}

    col1, col2 = st.columns([2, 1])
    with col1:
        profile_keys = ["<Neu>"] + list(profiles.keys())
        selected = st.selectbox("Vorhandene Profile", options=profile_keys, index=profile_keys.index(st.session_state.get("profile_selected", "<Neu>")))
        st.session_state.profile_selected = selected
    with col2:
        if st.button("Neu laden (Presets)"):
            cfg = load_profiles()
            profiles = cfg.get("profiles", {})

    if selected != "<Neu>":
        current = profiles.get(selected, {})
        defaults: Dict[str, Any] = current.copy()
    else:
        defaults = {}

    category_options = ["Low", "Medium", "High"]
    default_category = defaults.get("category", "Medium")
    category_index = category_options.index(default_category) if default_category in category_options else 1
    category = st.selectbox("Risikokategorie", options=category_options, index=category_index, help=TOOLTIPS["category"])

    if not defaults:
        defaults.update(CATEGORY_DEFAULTS.get(category, {}))
    else:
        if st.button("Mit Kategorie-Defaults überschreiben"):
            defaults.update(CATEGORY_DEFAULTS.get(category, {}))

    st.markdown("**Profilname**")
    profile_name = st.text_input("Profilname", value=defaults.get("display_name", "" if selected == "<Neu>" else selected), help=TOOLTIPS["profile_name"])

    st.markdown("**Asset Allocation (in %)**")
    eq = st.number_input("Equity (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("equity_pct", 0)), help=TOOLTIPS["equity_pct"])
    bd = st.number_input("Bonds (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("bond_pct", 0)), help=TOOLTIPS["bond_pct"])
    cs = st.number_input("Cash (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("cash_pct", 0)), help=TOOLTIPS["cash_pct"])

    auto_norm = st.checkbox("Auto-normalize auf 100%", value=True)
    if auto_norm:
        eq, bd, cs = normalize_weights(eq, bd, cs)

    # Universe laden (validierend)
    etf_universe, universe_warnings = load_etf_universe()

    macro_df = load_macro_data()
    price_data = load_price_data(etf_universe)
    regimes = detect_historical_regimes(macro_df)

    st.session_state["macro_df"] = macro_df
    st.session_state["price_data"] = price_data

    # 1. Aktuelles Regime bestimmen
    macro_regime = detect_regime(macro_df)

    # 2. ETF-Universum für dieses Regime auswählen
    allowed = select_etfs_for_regime(etf_universe, macro_regime)

    # 3. Portfolio für dieses Regime bauen
    portfolio = build_regime_portfolio(macro_regime, allowed)

    logger.debug("DEBUG: type(price_data)=", type(price_data), "shape=", getattr(price_data, "shape", None))
    logger.debug("DEBUG: portfolio=", portfolio)
    
    # 4. Backtest durchführen
    bt = run_backtest(portfolio, price_data, regimes)
    logger.debug("DEBUG: bt keys=", bt.keys() if isinstance(bt, dict) else type(bt))

    # 5. Performance analysieren
    stats = analyze_performance(bt)


    # 6. Ergebnisse nur schreiben, wenn vorhanden
    pv = bt.get("portfolio_value") if isinstance(bt, dict) else None
    metrics = bt.get("metrics") if isinstance(bt, dict) else {}
    logger.debug("DEBUG: metrics=", metrics)


    if pv is not None and not pv.empty:
        pv_df = pv.rename("portfolio_value").reset_index()
        # speichere DataFrame als dict oder als CSV‑String in session_state
        st.session_state["last_backtest_results_df"] = pv_df  # DataFrame direkt
        st.session_state["last_backtest_results_csv"] = pv_df.to_csv(index=False)
        logger.debug(f"DEBUG: backtest results stored in session_state, {len(pv_df)} Zeilen")
    else:
        logger.debug("DEBUG: portfolio_value leer — keine CSV geschrieben")

    if metrics:
        st.session_state["last_metrics"] = metrics
        logger.debug("DEBUG: results stored in session_state['last_metrics']")
    else:
        logger.debug("DEBUG: metrics leer — keine JSON geschrieben")


    st.write("Aktuelles Makro-Regime:", macro_regime)
    st.write("Portfolio:", portfolio)
    st.write("Backtest:", bt)
    st.write("Performance:", stats)

    if universe_warnings:
        for w in universe_warnings:
            st.warning(w)

    etf_options = {k: f"{v.get('name','')} ({v.get('ticker','')})" for k, v in etf_universe.items()}

    raw_defaults = defaults.get("allowed_instruments", []) if isinstance(defaults.get("allowed_instruments", []), list) else []
    default_etfs = [k for k in raw_defaults if k in etf_options]
    missing_defaults = [k for k in raw_defaults if k not in etf_options]
    if missing_defaults:
        st.warning("Einige voreingestellte Instrumente sind im aktuellen ETF-Universe nicht vorhanden: " + ", ".join(missing_defaults) + ". Bitte wähle Alternativen oder ergänze das etf_universe.yaml.")

    if not st.session_state.selected_etfs and default_etfs:
        st.session_state.selected_etfs = default_etfs.copy()

    st.markdown("**Erlaubte ETFs / Instrumente**")
    selected_etfs = st.multiselect("Wähle erlaubte ETFs (optional)", options=list(etf_options.keys()), format_func=lambda k: etf_options.get(k, k), default=st.session_state.selected_etfs, help="Wähle ETFs aus dem vordefinierten Universe. Du kannst eigene Keys verwenden.")
    if selected_etfs != st.session_state.selected_etfs:
        st.session_state.selected_etfs = selected_etfs

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Set Conservative ETFs"):
            apply_preset(["aggregate_bond_etf", "government_bonds", "investment_grade_corporates", "short_term_cash"], etf_universe)
    with col_b:
        if st.button("Set Balanced ETFs"):
            apply_preset(["global_equity_etf", "aggregate_bond_etf", "small_cap"], etf_universe)
    with col_c:
        if st.button("Set Aggressive ETFs"):
            apply_preset(["global_equity_etf", "emerging_markets", "small_cap"], etf_universe)

    resolved_holdings = resolve_components(st.session_state.selected_etfs, etf_universe)

    # Absolute Gewichte berechnen
    class_buckets: Dict[str, List[tuple]] = {"equity": [], "bond": [], "cash": []}
    for key, rel in resolved_holdings:
        meta = etf_universe.get(key, {})
        cls = meta.get("asset_class", "equity")
        class_buckets.setdefault(cls, []).append((key, rel))

    abs_weights: Dict[str, float] = {}
    def distribute(class_list: List[tuple], total_pct: float):
        total_rel = sum(w for _, w in class_list) or 1.0
        for k, w in class_list:
            abs_weights[k] = abs_weights.get(k, 0.0) + (w / total_rel) * (total_pct / 100.0)

    distribute(class_buckets.get("equity", []), eq)
    distribute(class_buckets.get("bond", []), bd)
    distribute(class_buckets.get("cash", []), cs)

    portfolio_vol = 0.0
    for key, w_abs in abs_weights.items():
        meta = etf_universe.get(key, {})
        asset_class = meta.get("asset_class", "equity")
        vol = vol_map.get(asset_class, 10)
        portfolio_vol += w_abs * vol

    if portfolio_vol < 6:
        auto_risk = "Low"
    elif portfolio_vol < 12:
        auto_risk = "Medium"
    else:
        auto_risk = "High"

    st.markdown(f"### Automatisch erkanntes Risiko: **{auto_risk}**")

    fig = go.Figure(go.Indicator(mode="gauge+number", value=portfolio_vol, title={"text": "Risiko-Thermometer"}, gauge={"axis": {"range": [0, 20]}, "bar": {"color": "red"}, "steps": [{"range": [0, 6], "color": "lightgreen"}, {"range": [6, 12], "color": "yellow"}, {"range": [12, 20], "color": "orange"}],},))
    st.plotly_chart(fig, width='stretch')

    with st.expander("Ausgewählte Instrumente und Paket‑Details"):
        rows = []
        for key, weight in resolved_holdings:
            meta = etf_universe.get(key, {})
            name = meta.get("name", key)
            ticker = meta.get("ticker", "")
            rows.append({"Key": key, "Name": name, "Ticker": ticker, "Weight": f"{weight*100:.1f}%"})
        st.table(rows)

    for sel in st.session_state.selected_etfs:
        item = etf_universe.get(sel, {})
        comps = item.get("components")
        if comps:
            with st.expander(f"Details: {item.get('name', sel)}"):
                st.markdown(f"**Key:** {sel}")
                st.markdown(f"**Ticker:** {item.get('ticker','-')}")
                st.markdown("**Komponenten:**")
                comp_rows = []
                total = sum(comps.values()) or 1.0
                for ck, w in comps.items():
                    comp_meta = etf_universe.get(ck, {})
                    comp_rows.append({"Key": ck, "Name": comp_meta.get("name", ck), "Ticker": comp_meta.get("ticker", ""), "Weight": f"{(w/total)*100:.1f}%"})
                st.table(comp_rows)

    
    # --- Expander: komplette Referenztabelle mit Suche ---
    with st.expander("Wichtige Kennzahlen (Kurzreferenz)"):
        query = st.text_input("Kennzahl suchen", value="")
        if query:
            hits = attr_df[attr_df["Attribut"].str.contains(query, case=False, na=False)]
            st.table(hits)
        else:
            st.table(attr_df)

    # --- Analyseergebnis (nur anzeigen, wenn vorhanden) ---
    used = st.session_state.get("analysis_used")
    metrics = st.session_state.get("analysis_metrics", {})
    if used is not None and metrics:
        st.subheader(f"Kennzahlen für {used}")
        st.table(pd.DataFrame([metrics]).T.rename(columns={0: "Wert"}))

        for k, label in label_map.items():
            value = metrics.get(k, None)
            explanation = attr_map.get(label, "")
            if value is not None:
                st.markdown(f"**{label}**: `{value:.4f}`")
            if explanation:
                st.caption(explanation)

    # --- Analyse Panel (weiter unten) ---
    with st.expander("Analyse Panel"):
        try:
            analyze_portfolio_components(
                etf_universe, resolved_holdings, eq, bd, cs, vol_map,
                ter_threshold_warn=0.01, herfindahl_warn=0.15
            )
        except Exception as e:
            st.warning(f"Analyse Panel konnte nicht ausgeführt werden: {e}")
     
    ###############
    # Hier könnte man weitere Abschnitte hinzufügen, z. B.: 
    #
    render_etf_tab(st.session_state)

    
    st.markdown("**Erlaubte Instrumente / Ausschlüsse (alternativ)**")
    allowed_text = st.text_area("Allowed instruments (Komma-getrennt)", value=",".join(st.session_state.selected_etfs) if st.session_state.selected_etfs else ",".join(defaults.get("allowed_instruments", [])), help=TOOLTIPS["allowed_instruments"])

    st.markdown("### 🔗 Abhängigkeiten & gültige Eingaben")
    valid_keys = list(etf_universe.keys())
    st.markdown("**Gültige ETF-Keys aus dem Universe:**")
    if valid_keys:
        st.code(", ".join(valid_keys))
    else:
        st.code("Keine ETFs im Universe definiert.")

    recommended_low = ["aggregate_bond_etf", "government_bonds", "investment_grade_corporates", "short_term_cash"]
    recommended_medium = ["global_equity_etf", "aggregate_bond_etf", "small_cap"]
    recommended_high = ["global_equity_etf", "emerging_markets", "small_cap"]

    st.markdown("**Empfohlene zusätzliche ETFs pro Risikoprofil:**")
    st.info(f"**Low Risk:** {', '.join(recommended_low)}  \n**Medium Risk:** {', '.join(recommended_medium)}  \n**High Risk:** {', '.join(recommended_high)}")

    def check_invalid(user_list):
        return [x for x in user_list if x not in valid_keys]

    if check_invalid(recommended_low) or check_invalid(recommended_medium) or check_invalid(recommended_high):
        st.warning("Einige empfohlene Keys existieren nicht im Universe. Bitte etf_universe.yaml prüfen/erweitern.")

    st.markdown("**Beschreibung / Notizen**")
    notes = st.text_area("Notes", value=defaults.get("notes", ""), help=TOOLTIPS["notes"])

    total = eq + bd + cs
    if abs(total - 100) > 0.5:
        st.warning(f"Summe Equity+Bonds+Cash = {total:.2f}%. Empfohlen: 100%. Nutze Auto-normalize oder passe Werte an.")

    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("Profil speichern"):
            key = (profile_name or selected or "custom_profile").strip().lower().replace(" ", "_")
            allowed_instruments = st.session_state.get("selected_etfs", [])
            if not allowed_instruments:
                allowed_instruments = [s.strip() for s in allowed_text.split(",") if s.strip()]
            profile_obj: Dict[str, Any] = {
                "display_name": profile_name or key,
                "category": category,
                "equity_pct": float(eq),
                "bond_pct": float(bd),
                "cash_pct": float(cs),
                "target_annual_return_pct": float(defaults.get("target_annual_return_pct", 5.0)),
                "max_drawdown_pct": float(defaults.get("max_drawdown_pct", 20)),
                "rebalance": defaults.get("rebalance", "monthly"),
                "allowed_instruments": allowed_instruments,
                "notes": notes,
            }
            save_profile(key, profile_obj)
            st.success(f"Profil '{profile_obj['display_name']}' gespeichert.")
            st.session_state.profile_selected = key

    with col_delete:
        if selected != "<Neu>" and st.button("Profil löschen"):
            cfg = load_profiles()
            profiles = cfg.get("profiles", {})
            if selected in profiles:
                profiles.pop(selected)
                cfg["profiles"] = profiles
                cfg_path = BASE_DIR / "config" / "profiles.yaml"
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                with cfg_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
                st.success(f"Profil '{selected}' gelöscht.")
                st.session_state.profile_selected = "<Neu>"
                st.session_state.selected_etfs = []

    st.markdown("---")
    st.info("Tipp: Wähle ein Risikoprofil (Low/Medium/High) um empfohlene Standardwerte zu laden. Nutze Auto-normalize, damit Equity+Bonds+Cash automatisch 100% ergeben.")

    with st.expander("Kurzlexikon und Quickstart"):
        if LEX_PATH.exists():
            st.markdown(LEX_PATH.read_text(encoding="utf-8"))
        else:
            st.write("Lexikon nicht gefunden. Bitte lege docs/lexikon.md an.")

