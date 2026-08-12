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
from risk_dashboard.core.utils import resolve_components, analyze_portfolio_components
from risk_dashboard.core.backtest import run_all_etf_backtests

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
from risk_dashboard.core.utils import classify_etf

logger = logging.getLogger(__name__)


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
    "iShares": "<URL_REMOVED>
    "Vanguard": "<URL_REMOVED>
    "Xtrackers": "<URL_REMOVED>
    "Amundi": "<URL_REMOVED>
    "Cash": "<URL_REMOVED>
    "Unbekannt": "<URL_REMOVED>
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
    # 1. Versuche session_state
    df = st.session_state.get(session_key)
    logger.debug("session_state keys: %s", list(st.session_state.keys()))
    logger.debug("portfolio_df present in session: %s", session_key in st.session_state)

    # 2. File uploader (UI) — eindeutiger key
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

    # 3. Fallback: Datei auf Disk
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

    # 4. Kein Portfolio gefunden -> leeres DataFrame
    logger.debug("No portfolio found; returning empty DataFrame")
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_from_api(ticker: str, api_key: str) -> pd.DataFrame:
    url = "<URL_REMOVED>
    params = {"key": api_key, "ticker": ticker}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("result", {}).get("holdings", [])
    return pd.DataFrame([{"ticker":h["ticker"], "weight_in_etf": float(h["percent_value"])/100} for h in data])

@st.cache_data(ttl=3600)
def fetch_from_provider_csv(ticker: str) -> pd.DataFrame:
    # Beispiel: iShares/Vanguard bieten CSV-Links; hier musst du die konkrete URL-Logik implementieren
    csv_url = f"<URL_REMOVED>  # placeholder
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

def get_etf_holdings(ticker: str, api_key: str | None = None) -> pd.DataFrame:
    """Versucht API -> CSV -> etf_scraper. Gibt DataFrame oder pd.DataFrame() zurück."""
    logger = logging.getLogger(__name__)

    # 1. API
    try:
        if api_key:
            df = fetch_from_api(ticker, api_key)
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.debug("Holdings from API for %s: %d rows", ticker, len(df))
                return df
    except Exception as e:
        logger.exception("API holdings failed for %s: %s", ticker, e)

    # 2. Provider CSV
    try:
        df = fetch_from_provider_csv(ticker)
        if isinstance(df, pd.DataFrame) and not df.empty:
            logger.debug("Holdings from provider CSV for %s: %d rows", ticker, len(df))
            return df
    except Exception as e:
        logger.exception("Provider CSV failed for %s: %s", ticker, e)

    # 3. etf_scraper fallback
    try:
        from etf_scraper import ETFScraper
        s = ETFScraper()
        hdf = s.query_holdings(ticker)
        if hdf is None or len(hdf) == 0:
            logger.warning("etf_scraper returned no holdings for %s", ticker)
            return pd.DataFrame()
        df = pd.DataFrame({"ticker": hdf["ticker"], "weight_in_etf": hdf["weight"] / 100.0})
        logger.debug("Holdings from etf_scraper for %s: %d rows", ticker, len(df))
        return df
    except Exception as e:
        logger.exception("etf_scraper fallback failed for %s: %s", ticker, e)

    # Fallback: leeres DF
    logger.warning("No holdings found for %s (all sources failed)", ticker)
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


    # 1. Portfolio Input
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

    # 2. Auswahl ETFs aus Portfolio
    tickers = df["ticker"].astype(str).str.upper().unique().tolist() if not df.empty else []
    selected_etfs = st.multiselect("Aus Portfolio wähle ETF(s) zur Aufschlüsselung", options=tickers)

    # 3. Holdings pro ETF
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

        # 1. CSV Upload
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

        # 2. iShares Internet‑Holdings (nur wenn Checkbox gesetzt)
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

            # 1. Versuche relaxed fallback (einfaches ticker,weight_in_etf CSV)
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

            # 2. relaxed nicht verwendet -> bestehende Logik ausführen
            hdf = load_holdings_with_fallback(etf, category, isin, df_key, holdings_dir)

            # 3. iShares / Demo Logik (nur hier, nicht vorher)
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

    st.markdown("---")
    st.info("Tipp: Wähle ein Risikoprofil (Low/Medium/High) um empfohlene Standardwerte zu laden. Nutze Auto-normalize, damit Equity+Bonds+Cash automatisch 100% ergeben.")

    with st.expander("Kurzlexikon und Quickstart"):
        if LEX_PATH.exists():
            st.markdown(LEX_PATH.read_text(encoding="utf-8"))
        else:
            st.write("Lexikon nicht gefunden. Bitte lege docs/lexikon.md an.")