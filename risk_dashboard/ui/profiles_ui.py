# risk_dashboard/ui/profiles_ui.py
"""
Streamlit UI for managing portfolio profiles (presets) with validation and analysis.
"""
from pathlib import Path
import sys
import traceback
from typing import Dict, Any, Tuple, Optional, List, Sequence
from io import StringIO
import numpy as np
import requests
import plotly.graph_objects as go
import pandas as pd
from datetime import date

from rich import region
import streamlit as st
import yaml
import tempfile, os, json
import logging, inspect, pathlib

from risk_dashboard.core.data import portfolio
from risk_dashboard.etf_candidates import add_etf_candidates
from risk_dashboard.data_utils import fetch_price_history_bulk, price_history_to_prices_df
from risk_dashboard.core.screening import screen_and_rank
from risk_dashboard.core.config import load_profiles, save_profile, load_etf_universe
from risk_dashboard.core.utils import resolve_components, analyze_portfolio_components, classify_etf
from risk_dashboard.ui.helpers  import render_backtest, normalize_ticker, detect_type, safe_backtest_call

from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.holdings import load_ishares_holdings, etf_to_isin_map, load_holdings_with_fallback
from risk_dashboard.core.macro_pipeline import (
    detect_regime,
    select_etfs_for_regime,
    build_regime_portfolio,
    _fetch_and_clean_prices,
    analyze_performance
)

from risk_dashboard.core.holdings import try_relaxed_holdings
from risk_dashboard.core.etf_tools import download_prices
from risk_dashboard.core.macro_loader import load_and_validate_macro_data
from risk_dashboard.core.data_loader import parse_tickers, load_price_data
from risk_dashboard.config import DEFAULT_START_STR, DEFAULT_END_STR, ALLOW_TEST_UNIVERSE,UNIVERSE_PATHS
from risk_dashboard.data_utils import safe_rerun

logger = logging.getLogger(__name__)

logger.debug("load_and_validate_macro_data module: %s", load_and_validate_macro_data.__module__)
try:
    logger.debug("load_and_validate_macro_data file: %s", inspect.getsourcefile(load_and_validate_macro_data))
except Exception:
    logger.debug("could not determine source file for load_and_validate_macro_data")

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
            # Optional: einfache Validierung
            if "ticker" not in [c.lower() for c in df.columns]:
                st.warning("Die CSV enthält keine Spalte 'ticker' (Groß-/Kleinschreibung beachten).")
            st.session_state[session_key] = df
            st.success("Portfolio erfolgreich geladen.")
            return df
        except Exception as e:
            logger.exception("Failed to parse uploaded portfolio CSV: %s", e)
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

# --- Helper für defensive Nicht-Leer Prüfungen ---
def is_nonempty_old(obj):
    if obj is None:
        return False
    if hasattr(obj, "empty"):
        return not obj.empty
    try:
        return bool(len(obj))
    except Exception:
        return True

def is_nonempty(x) -> bool:
    if x is None:
        return False
    # pandas DataFrame
    if isinstance(x, pd.DataFrame):
        return not x.empty
    # pandas Series
    if isinstance(x, pd.Series):
        return not x.empty
    # iterables: list/tuple/set/dict
    if isinstance(x, (list, tuple, set, dict)):
        return len(x) > 0
    # fallback for scalars
    try:
        return bool(x)
    except Exception:
        return False

# 5. Ticker extrahieren (anpassbar an dein Portfolio-Format)
def _extract_tickers_from_portfolio(p):
    # dict mit bekannten keys
    if isinstance(p, dict):
        for key in ("tickers","assets","positions","holdings","components"):
            val = p.get(key)
            if val:
                return list(val) if not isinstance(val, str) else [val]
    # DataFrame mit Spaltennamen
    if hasattr(p, "columns"):
        return list(p.columns)
    # Series mit index als tickers
    if hasattr(p, "index") and not hasattr(p, "columns"):
        try:
            return list(p.index)
        except Exception:
            pass
    # Liste von tuples/dicts
    if isinstance(p, (list, tuple)):
        # list of (ticker, weight) or list of dicts
        tickers = []
        for item in p:
            if isinstance(item, (list, tuple)) and len(item) >= 1:
                tickers.append(item[0])
            elif isinstance(item, dict):
                for key in ("ticker","symbol","asset"):
                    if key in item:
                        tickers.append(item[key])
                        break
        return tickers
    return []
    

def render_etf_tab(session_state=None):
    # --- Dashboard‑Dokumentation / Gebrauchsanweisung ---
    # --- Beginn bereinigter Abschnitt in render_etf_tab ---
    ss = st.session_state
    ss.setdefault("user_weights_mapped", {})
    ss.setdefault("run_in_progress", False)
    ss.setdefault("DEBUG", False)

    # Dokumentation Expander (unverändert)
    with st.expander("📘 Dashboard‑Beschreibung und Gebrauchsanweisung"):
        DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "dashboard_guide.md"
        if DOC_PATH.exists():
            st.markdown(DOC_PATH.read_text(encoding="utf-8"))
        else:
            st.write("Dokumentation nicht gefunden. Bitte lege docs/dashboard_guide.md an.")

    # Portfolio laden (defensiv)
    df = ss.get("portfolio_df", pd.DataFrame())
    if df.empty:
        try:
            loaded_df = load_portfolio_from_ui_or_disk()
            if isinstance(loaded_df, pd.DataFrame) and not loaded_df.empty:
                df = loaded_df
                ss["portfolio_df"] = df
        except Exception:
            logger.exception("load_portfolio_from_ui_or_disk failed")

    if not df.empty:
        st.dataframe(df)

    # ganz oben in der Funktion
    prefix = ss.get("prefix", "profile")

    # Portfolio Input
    auto_portfolio_value = compute_portfolio_value(df) if not df.empty else 0.0
    portfolio_value = st.number_input(
        "Gesamtportfolio (leer = Summe der Marktwerte)",
        value=float(auto_portfolio_value),
        format="%.2f",
        key=f"{prefix}_portfolio_value"
    )
    ss["portfolio_value"] = float(portfolio_value)

    # Auswahl aus Portfolio
    tickers = df["ticker"].astype(str).str.upper().unique().tolist() if not df.empty else []
    selected_from_portfolio = st.multiselect(
        "Aus Portfolio wähle ETF(s) zur Aufschlüsselung",
        options=tickers,
        key=f"{prefix}_portfolio_selected_etfs"
    )

    # Session Werte
    etf_universe = ss.get("etf_universe", {}) or {}
    price_data = ss.get("price_data")
    macro_df = ss.get("macro_df")
    
    # 1) Universe prüfen und ggf. Test‑Universe setzen
    if not etf_universe:
        if ALLOW_TEST_UNIVERSE:
            etf_universe = {t: {"ticker": t} for t in ["VWRL.L", "CSPX.L"]}
            ss["etf_universe"] = etf_universe
            logger.info("Using test universe (dev mode)")
        else:
            st.info("Keine vordefinierten ETFs gefunden. Bitte füge Kandidaten im Profil hinzu.")
            if st.button("Profil öffnen: Kandidaten hinzufügen", key=f"{prefix}_open_profile_editor"):
                ss["show_profile_editor"] = True
                safe_rerun()
            return

    # 2) Optionen bauen
    etf_options = {k: v.get("display_name", k) for k, v in ss.get("etf_universe", {}).items()}
    options = list(etf_options.keys())

    # 3) Defaults defensiv filtern
    raw_selected = ss.get("selected_etfs", []) or []
    logger.debug("raw selected_etfs before filter: %s", raw_selected)
    logger.debug("etf_universe keys sample: %s", list(etf_universe.keys())[:50])

    defaults = [v for v in raw_selected if v in options]
    if len(defaults) != len(raw_selected):
        logger.warning("Filtered invalid selected_etfs: %s -> %s", raw_selected, defaults)
        ss["selected_etfs"] = defaults
    
    # 4) Defensive UI falls options leer
    if not options:
        st.info("Keine vordefinierten ETFs gefunden. Bitte füge Kandidaten im Profil hinzu.")
        if st.button("Profil öffnen: Kandidaten hinzufügen", key=f"{prefix}_open_profile_editor"):
            ss["show_profile_editor"] = True
            safe_rerun()
        return

    # 5) Multiselect mit gefilterten Defaults
    selected_etfs = st.multiselect(
        "Wähle erlaubte ETFs (optional)",
        options=options,
        default=defaults,
        key=f"{prefix}_selected_etfs",
        help="Wähle ETFs aus dem vordefinierten Universe."
    )
    ss["selected_etfs"] = selected_etfs

    # Debug nur bei Flag
    if ss.get("DEBUG"):
        st.write("DEBUG price_path:", globals().get("price_path"))
        st.write("DEBUG macro_path:", globals().get("macro_path"))

    # Annahme: ss = st.session_state; prefix ist gesetzt; logger importiert
    # --- KI Vorschläge mit eindeutigen Keys ---
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("KI Vorschlag: Konservativ", key=f"{prefix}_ki_conservative"):
            ss["user_weights_mapped"] = {"CASH": 0.2, "BOND": 0.5, "EQUITY": 0.3}  # Beispiel
            safe_rerun()
    with col2:
        if st.button("KI Vorschlag: Ausgewogen", key=f"{prefix}_ki_balanced"):
            ss["user_weights_mapped"] = {"CASH": 0.1, "BOND": 0.4, "EQUITY": 0.5}
            safe_rerun()
    with col3:
        if st.button("KI Vorschlag: Wachstum", key=f"{prefix}_ki_growth"):
            ss["user_weights_mapped"] = {"CASH": 0.0, "BOND": 0.2, "EQUITY": 0.8}
            safe_rerun()

    # Defensive defaults for session keys
    ss.setdefault("user_weights_mapped", {})
    ss.setdefault("run_in_progress", False)
    ss.setdefault("selected_etfs", [])

    st.json(ss.get("user_weights_mapped", {}))

    # JSON Editor (defensiv): value aus session holen, nicht direkt aus st.json-Ausgabe
    weights_text = st.text_area(
        "Gewichte als JSON bearbeiten",
        value=json.dumps(ss.get("user_weights_mapped", {}), indent=2),
        height=120,
        key=f"{prefix}_weights_text"
    )
    try:
        parsed = json.loads(weights_text)
        total = sum(parsed.values()) if isinstance(parsed, dict) else 0.0
        st.write(f"Summe Gewichte: {total:.4f}")
        if st.button("Übernehme geänderte Gewichte", key=f"{prefix}_apply_weights"):
            ss["user_weights_mapped"] = {k: float(v) for k, v in parsed.items()}
            safe_rerun()
    except Exception as e:
        st.error("Ungültiges JSON: " + str(e))

    # --- Berechnen Button (defensiv) ---
    # ensure selected_etfs variable exists in scope (from earlier multiselect)
    selected_etfs = ss.get("selected_etfs", [])

    if st.button("Berechnen", key=f"{prefix}_btn_etf_calculate", disabled=ss["run_in_progress"]):
        ss["run_in_progress"] = True
        try:
            pd_shared = ss.get("price_data")
            md_shared = ss.get("macro_df")
            user_weights_mapped = ss.get("user_weights_mapped", {})

            # Validierungen
            if pd_shared is None or md_shared is None:
                st.error("Preisdaten oder Makrodaten fehlen.")
                ss["run_in_progress"] = False
                return

            if not user_weights_mapped:
                st.warning("Keine Gewichte gesetzt.")
                ss["run_in_progress"] = False
                return

            # Sanity Check
            from risk_dashboard.data_utils import sanity_backtest
            ok, msg = sanity_backtest(pd_shared, user_weights_mapped, min_rows=60)
            if not ok:
                st.error("Sanity Check fehlgeschlagen: " + msg)
                ss["run_in_progress"] = False
                return

            # Debug log der Inputs
            logger.debug(
                "Backtest inputs: selected_etfs=%s, user_weights=%s, price_data_keys=%s",
                selected_etfs,
                user_weights_mapped,
                None if pd_shared is None else list(pd_shared.columns)[:10]
            )

            with st.spinner("Backtests laufen, bitte warten…"):
                from risk_dashboard.core.backtest import run_all_etf_backtests
                out = run_all_etf_backtests(
                    selected_etfs=selected_etfs,
                    holdings_dir=holdings_dir,
                    etf_to_isin_map=etf_to_isin_map,
                    price_data=pd_shared,
                    macro_df=md_shared,
                    backtest_dir=Path("risk_dashboard/data/backtests"),
                    portfolio_value=ss.get("portfolio_value", 100000.0),
                    threads=False,
                )

            st.success("Backtests abgeschlossen.")
            st.json(out)

        except Exception as e:
            logger.exception("Backtest failed: %s", e)
            st.error(f"Backtest fehlgeschlagen: {e}")
        finally:
            ss["run_in_progress"] = False

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

def profile_form_ui(
    etf_universe: Optional[Dict] = None,
    universe_warnings: Optional[Any] = None,
    macro_df: Optional[pd.DataFrame] = None,
    price_data: Optional[pd.DataFrame] = None,
    index_choice: Optional[str] = None,
    prefix: str = "profile",
) -> None:

    ss = st.session_state
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
        selected = st.selectbox("Vorhandene Profile", options=profile_keys, index=profile_keys.index(st.session_state.get("profile_selected", "<Neu>")), key="profiles_existing_profile_select")

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
    category = st.selectbox("Risikokategorie", options=category_options, index=category_index, help=TOOLTIPS["category"], key="profiles_risk_category_select")

    if not defaults:
        defaults.update(CATEGORY_DEFAULTS.get(category, {}))
    else:
        if st.button("Mit Kategorie-Defaults überschreiben"):
            defaults.update(CATEGORY_DEFAULTS.get(category, {}))

    st.markdown("**Profilname**")
    profile_name = st.text_input("Profilname", value=defaults.get("display_name", "" if selected == "<Neu>" else selected), help=TOOLTIPS["profile_name"],key="profile_name_input")

    st.markdown("**Asset Allocation (in %)**")
    eq = st.number_input("Equity (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("equity_pct", 0)), help=TOOLTIPS["equity_pct"])
    bd = st.number_input("Bonds (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("bond_pct", 0)), help=TOOLTIPS["bond_pct"])
    cs = st.number_input("Cash (%)", min_value=0.0, max_value=100.0, value=float(defaults.get("cash_pct", 0)), help=TOOLTIPS["cash_pct"])

    auto_norm = st.checkbox("Auto-normalize auf 100%", value=True)
    if auto_norm:
        eq, bd, cs = normalize_weights(eq, bd, cs)

    # --- Daten einmalig laden und in session_state speichern ---
    
    # Defensive fallbacks: Parameter -> session_state -> loader (only as last resort)
    etf_universe = etf_universe or st.session_state.get("etf_universe") or {}
    universe_warnings = universe_warnings or st.session_state.get("universe_warnings")
    if price_data is None:
        price_data = st.session_state.get("price_data")

    # Load stock universe (static file) — use project path, handle missing file
    try:
        stock_universe = pd.read_csv("risk_dashboard/data/stock_universe.csv")
    except Exception as e:
        logger.exception("Failed to load stock_universe.csv: %s", e)
        stock_universe = None

    def build_combined_universe(etf_universe, stock_universe):
        """
        Robust: akzeptiert DataFrame, dict (ticker->meta) oder list(dict).
        Liefert ein DataFrame mit Spalte 'ticker' und 'asset_type' oder None.
        """
        parts = []

        def to_df(obj, asset_type):
            # None -> None
            if obj is None:
                return None
            # already a DataFrame
            if isinstance(obj, pd.DataFrame):
                df = obj.copy()
                df["asset_type"] = asset_type
                # ensure ticker column exists
                if "ticker" not in df.columns:
                    # try to infer from index or keys
                    if df.index.nlevels == 1:
                        df = df.reset_index().rename(columns={df.index.name or 0: "ticker"})
                    else:
                        raise ValueError(f"DataFrame for {asset_type} has no 'ticker' column")
                df["ticker"] = df["ticker"].astype(str)
                return df
            # dict mapping ticker -> meta
            if isinstance(obj, dict):
                rows = []
                for k, v in obj.items():
                    # if v is dict with metadata, merge
                    if isinstance(v, dict):
                        row = {"ticker": str(k)}
                        row.update(v)
                    else:
                        row = {"ticker": str(k), "meta": v}
                    rows.append(row)
                df = pd.DataFrame(rows)
                df["asset_type"] = asset_type
                return df
            # list of dicts (rows)
            if isinstance(obj, (list, tuple)):
                try:
                    df = pd.DataFrame(obj)
                    if "ticker" not in df.columns:
                        raise ValueError(f"List for {asset_type} has no 'ticker' field")
                    df["asset_type"] = asset_type
                    df["ticker"] = df["ticker"].astype(str)
                    return df
                except Exception:
                    raise
            # unknown type
            raise TypeError(f"Unsupported universe type: {type(obj)} for {asset_type}")

        # convert both universes
        try:
            df_etf = to_df(etf_universe, "ETF")
        except Exception as e:
            logger.exception("Failed to coerce etf_universe to DataFrame: %s", e)
            df_etf = None

        try:
            df_stock = to_df(stock_universe, "Stock")
        except Exception as e:
            logger.exception("Failed to coerce stock_universe to DataFrame: %s", e)
            df_stock = None

        if df_etf is not None:
            parts.append(df_etf)
        if df_stock is not None:
            parts.append(df_stock)

        if not parts:
            return None

        combined = pd.concat(parts, ignore_index=True, sort=False)
        combined = combined.drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)
        combined["ticker"] = combined["ticker"].astype(str)
        return combined


    def debug_universe_shape(name, obj):
        if obj is None:
            logger.debug("%s is None", name)
        elif isinstance(obj, pd.DataFrame):
            logger.debug("%s is DataFrame columns=%s rows=%s", name, list(obj.columns), len(obj))
        elif isinstance(obj, dict):
            logger.debug("%s is dict with %d keys; sample keys=%s", name, len(obj), list(obj.keys())[:10])
        elif isinstance(obj, (list, tuple)):
            logger.debug("%s is list/tuple len=%d sample0=%s", name, len(obj), obj[0] if obj else None)
        else:
            logger.debug("%s is %s", name, type(obj))

    debug_universe_shape("etf_universe", etf_universe)
    debug_universe_shape("stock_universe", stock_universe)

    st.session_state["combined_universe"] = build_combined_universe(etf_universe, stock_universe)

    # prefer explicit None-checks; avoid "or" with DataFrame objects
    if macro_df is None:
        macro_df = st.session_state.get("macro_df")

    # --- Macro Data und Regimes initialisieren und persistieren ---
    if "macro_df" not in st.session_state:
        try:
            st.session_state["macro_df"] = load_and_validate_macro_data()
        except Exception as e:
            logger.exception("load_and_validate_macro_data failed: %s", e)
            st.session_state["macro_df"] = None

    macro_df = st.session_state.get("macro_df")

    # Wenn keine Makrodaten vorhanden sind, sauber abbrechen
    if macro_df is None or (isinstance(macro_df, pd.DataFrame) and macro_df.empty):
        st.error("Makrodaten fehlen oder sind unvollständig. Vorgang abgebrochen.")
        return

    # Regimes nur einmal berechnen und in session_state speichern
    if "regimes" not in st.session_state or not is_nonempty(st.session_state.get("regimes")):
        try:
            regimes = detect_historical_regimes(macro_df)
            if is_nonempty(regimes):
                st.session_state["regimes"] = regimes
                logger.debug("regimes computed and stored in session_state")
            else:
                st.session_state["regimes"] = None
                logger.warning("detect_historical_regimes returned empty result")
        except Exception as e:
            logger.exception("Failed to compute regimes: %s", e)
            st.session_state["regimes"] = None
            st.error("Fehler beim Berechnen der Regime. Siehe Logs.")

    # Aktuelles Regime berechnen, nur wenn macro_df valide ist
    if macro_df is not None and isinstance(macro_df, pd.DataFrame) and not macro_df.empty:
        try:
            macro_regime = detect_regime(macro_df)
        except Exception as e:
            logger.exception("detect_regime failed: %s", e)
            macro_regime = None
    else:
        macro_regime = None


    # Debug globaler Session-Status (nur dev)
    if ss.get("DEBUG"):
        st.write("profile_form_ui session_state keys:", list(ss.keys()))
        logger.debug("profile_form_ui session_state keys: %s", list(ss.keys()))

    # Wenn du einen DuplicateKey vermutest, logge direkt vor der selectbox
    logger.debug("About to render index selectbox with key=%s", f"{prefix}_local_index_choice")
    if index_choice is None:
        index_choice = st.selectbox(
            "Index / Universe wählen",
            list(UNIVERSE_PATHS.keys()),
            index=1,
            key=f"{prefix}_local_index_choice"
        )

    # ab hier: index_choice ist gesetzt und darf verwendet werden
    path_index_choice = UNIVERSE_PATHS.get(index_choice)

    # Safe logging: etf_universe may be None or dict
    try:
        etf_type = type(etf_universe)
        etf_len = len(etf_universe) if etf_universe is not None else None
        etf_sample = list(etf_universe)[:10] if isinstance(etf_universe, dict) and etf_universe else None
        logger.debug("etf_universe type=%s len=%s sample=%s", etf_type, etf_len, etf_sample)
    except Exception:
        logger.exception("Error while logging etf_universe")

    def render_candidate_editor(prefix: str, index_choice: str, asset_type: str):
        new_key = f"{prefix}_new_etfs_input"
        save_key = f"{prefix}_save_candidates"
        st.text_input("Kommaseparierte ETFs hinzufügen (z.B. EUNL.DE, CSPX.L)", key=new_key)
        if st.button("Kandidaten speichern", key=save_key):
            raw = st.session_state.get(new_key, "")
            tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
            if not tickers:
                st.warning("Keine gültigen Ticker eingegeben.")
                return

            try:
                # tickers: Liste der neu eingegebenen Ticker (bereits .upper() normalisiert)
                add_etf_candidates(index_choice, tickers, asset_type=asset_type)

                # 1) Universe neu laden (falls add_etf_candidates nicht automatisch updated)
                # path_index_choice = st.session_state.get("path_index_choice") or UNIVERSE_PATHS.get(index_choice)
                if path_index_choice:
                    new_universe, warnings = load_etf_universe(path_index_choice)
                    # optional: normalisiere keys
                    new_universe = {k.upper(): v for k, v in new_universe.items()}
                    st.session_state["etf_universe"] = new_universe
                else:
                    # Fallback: erweitere vorhandenes Universe
                    eu = st.session_state.get("etf_universe", {})
                    for t in tickers:
                        eu.setdefault(t.upper(), {"ticker": t.upper()})
                    st.session_state["etf_universe"] = eu

                # 2) Filter / Merge selected_etfs
                prev = st.session_state.get("selected_etfs", [])
                prev_norm = [p.upper().strip() for p in prev]
                valid = [p for p in prev_norm if p in st.session_state["etf_universe"]]
                # füge neu hinzu, damit Nutzer sie sofort sieht
                for t in tickers:
                    if t in st.session_state["etf_universe"] and t not in valid:
                        valid.append(t)
                st.session_state["selected_etfs"] = valid

                # 3) Caches invalidieren + Rerun
                st.session_state.pop("combined_universe", None)
                st.session_state.pop("price_data", None)
                st.session_state["show_profile_editor"] = False
                safe_rerun()
                return
            except Exception as e:
                logger.exception("Fehler beim Hinzufügen von Kandidaten: %s", e)
                st.error("Fehler beim Hinzufügen der Kandidaten. Siehe Log.")
                return

    # If universe empty: allow user to add candidates or use test universe
    # profiles_ui.py (oder wo Test‑Universe gesetzt wird)
    if not etf_universe:
        if ALLOW_TEST_UNIVERSE:
            # Dev only: set test universe
            etf_universe = {t: {"ticker": t} for t in ["VWRL.L", "CSPX.L"]}
            logger.info("Using test universe (dev mode)")
        else:
            # Production: force user action
            st.info("Keine vordefinierten ETFs gefunden. Bitte füge Kandidaten hinzu.")
            # show input widgets but do NOT auto-populate
            # Aufruf nur einmal pro gewünschtem Editor:
            render_candidate_editor(prefix="etf", index_choice="global", asset_type="ETF")
            # Wenn du wirklich zwei Editoren willst, rufe mit unterschiedlichen prefix/index_choice auf:
            # render_candidate_editor(prefix="stock", index_choice="stocks", asset_type="Stock")
            
    # price_data: fallback to session_state, loader only as last resort

    # 1) Fallback aus session_state, aber ohne "or" mit DataFrame
    if price_data is None:
        price_data = st.session_state.get("price_data")

    # 2) Defensive Extraktion von Tickers aus etf_universe
    def extract_tickers_from_universe(universe_meta):
        """
        Robust: accepts None, dict, DataFrame, list/tuple/set and returns list[str].
        """
        if universe_meta is None:
            return []

        if isinstance(universe_meta, dict):
            tickers = []
            for v in universe_meta.values():
                if isinstance(v, dict):
                    t = v.get("ticker") or v.get("tickers") or v.get("symbol")
                    if t:
                        tickers.append(str(t))
                elif isinstance(v, str):
                    tickers.append(v)
            return list(dict.fromkeys([t for t in tickers if t]))

        if isinstance(universe_meta, pd.DataFrame):
            # prefer explicit columns
            for col in ("ticker", "tickers", "symbol", "symbols"):
                if col in universe_meta.columns:
                    return universe_meta[col].dropna().astype(str).tolist()
            # fallback: index if looks like tickers
            try:
                idx = universe_meta.index.astype(str)
                if all(len(x) > 0 for x in idx):
                    return idx.tolist()
            except Exception:
                pass
            # last resort: first object column
            for col in universe_meta.columns:
                if universe_meta[col].dtype == object:
                    vals = universe_meta[col].dropna().astype(str).tolist()
                    if vals:
                        return vals
            return []

        if isinstance(universe_meta, (list, tuple, set)):
            tickers = []
            for item in universe_meta:
                if isinstance(item, str):
                    tickers.append(item)
                elif isinstance(item, dict):
                    t = item.get("ticker") or item.get("symbol")
                    if t:
                        tickers.append(str(t))
            return list(dict.fromkeys([t for t in tickers if t]))

        logger.warning("extract_tickers_from_universe: unsupported type %s", type(universe_meta))
        return []

    # --- Verwendung in deiner UI ---
    tickers_list = extract_tickers_from_universe(etf_universe)
    logger.debug("tickers_list extracted from etf_universe: %s", tickers_list)

    # 3) Loader nur aufrufen, wenn wir tatsächlich Ticker haben
    if price_data is None:
        if not tickers_list:
            logger.warning("load_price_data skipped: no tickers to download (etf_universe empty)")
            price_data = None
        else:
            try:
                # Entweder load_price_data akzeptiert etf_universe oder eine ticker-liste.
                # Falls es Ticker-Liste erwartet, übergib tickers_list; sonst etf_universe.
                price_data = load_price_data(tickers_list)  # oder load_price_data(etf_universe)
                if is_nonempty(price_data):
                    st.session_state["price_data"] = price_data
                else:
                    price_data = None
            except Exception as e:
                logger.exception("load_price_data failed: %s", e)
                price_data = None

    # 4) Wenn noch keine Preisdaten: Upload-UI anbieten (kein sofortiger return)
    if not is_nonempty(price_data):
        logger.warning("profile_form_ui: price_data fehlt oder ist leer; zeige Upload-UI")
        st.warning("Preisdaten konnten nicht geladen werden. Bitte überprüfe die Verbindung oder wähle andere ETFs.")
        uploaded_prices = st.file_uploader(
            "CSV mit Preisdaten hochladen (Date mit Datum und Close)",
            type=["csv"],
            key="prices_uploader_profile"
        )
        if uploaded_prices is not None:
            try:
                df = pd.read_csv(uploaded_prices, parse_dates=["Date"]).set_index("Date").sort_index()
                if "Close" not in df.columns and df.shape[1] == 1:
                    df.columns = ["Close"]
                if is_nonempty(df):
                    st.session_state["price_data"] = df
                    price_data = df
                    st.success("Preisdaten erfolgreich hochgeladen.")
                    # st.experimental_rerun()
                    safe_rerun()
                else:
                    st.error("Hochgeladene Datei enthält keine gültigen Preisdaten.")
            except Exception as e:
                logger.exception("Fehler beim Einlesen der Preisdaten: %s", e)
                st.error("Fehler beim Einlesen der Preisdaten.")

    # Build portfolio only when price_data is available
    portfolio = st.session_state.get("selected_portfolio")
    # compute macro_regime only when macro_df is a non-empty DataFrame
    if macro_df is not None and isinstance(macro_df, pd.DataFrame) and not macro_df.empty:
        try:
            macro_regime = detect_regime(macro_df)
        except Exception as e:
            logger.exception("detect_regime failed: %s", e)
            macro_regime = None
    else:
        macro_regime = None

    allowed = select_etfs_for_regime(etf_universe, macro_regime)

    if is_nonempty(price_data):
        try:
            portfolio = build_regime_portfolio(macro_regime, allowed, prices=price_data, method="HRP")
        except ValueError as e:
            logger.exception("build_regime_portfolio fehlgeschlagen: %s", e)
            st.error("Portfolio konnte nicht erstellt werden: Preisdaten fehlen oder sind unvollständig.")
            portfolio = None
        else:
            st.session_state["selected_portfolio"] = portfolio

    # If no portfolio, stop UI flow (user must upload/select)
    if not portfolio:
        logger.debug("No selected_portfolio available; skipping ticker extraction")
        st.info("Kein Portfolio verfügbar. Bitte lade Preisdaten oder wähle ein Portfolio.")
        st.stop()

    # Extract tickers and validate against price_data
    tickers = _extract_tickers_from_portfolio(portfolio)
    if not tickers:
        st.warning("Kein Portfolio mit Tickers gefunden.")
        st.stop()

    available = [
        t for t in tickers
        if price_data is not None and hasattr(price_data, "columns") and t in price_data.columns.tolist()
    ]
    if not available:
        st.error("Keine Portfolio‑Ticker in Preisdaten vorhanden.")
        st.stop()
    # Weiterverarbeitung hier...

    bt = {}
    
    from risk_dashboard.utils.backtest_adapter import adapter_run_backtest  # falls benötigt

    def normalize_and_unique(tickers):
        seen = set()
        out = []
        for t in tickers or []:
            if not t:
                continue
            tn = str(t).strip().upper()
            if tn and tn not in seen:
                seen.add(tn)
                out.append(tn)
        return out

    def _get_tickers_from_portfolio_struct(p):
        if isinstance(p, dict):
            if "tickers" in p and p["tickers"]:
                return list(p["tickers"])
            if "weights" in p and isinstance(p["weights"], dict):
                return list(p["weights"].keys())
        if isinstance(p, (list, tuple)):
            return list(p)
        return []

    # 1) Regimes prüfen frühzeitig (alte Logik übernommen)
    regimes_val = st.session_state.get("regimes")
    if not is_nonempty(regimes_val):
        logger.warning("profile_form_ui: 'regimes' nicht definiert oder leer.")
        st.error("Regime-Daten fehlen oder sind leer. Backtest abgebrochen.")
        st.stop()

    # 2) Tickerquellen normalisieren
    tickers_from_portfolio = normalize_and_unique(_extract_tickers_from_portfolio(portfolio))
    logger.debug("tickers_from_portfolio: %s", tickers_from_portfolio)

    tickers_ui = normalize_and_unique([a.get("ticker") for a in st.session_state.get("selected_assets", [])])
    logger.debug("tickers_ui: %s", tickers_ui)

    # 3) Entscheide, welche Ticker verwendet werden (UI bevorzugen, sonst Portfolio)
    tickers_to_use = tickers_ui or tickers_from_portfolio
    if not tickers_to_use:
        st.error("Keine Ticker ausgewählt oder im Portfolio gefunden.")
        st.stop()

    # 4) Preise laden und normalisieren
    price_history = fetch_price_history_bulk(tickers_to_use)
    price_history = {str(k).strip().upper(): v for k, v in price_history.items()}
    prices_df = price_history_to_prices_df(price_history)
    if hasattr(prices_df, "columns"):
        prices_df.columns = [str(c).strip().upper() for c in prices_df.columns]

    # 5) Verfügbare Ticker prüfen
    available = [t for t in tickers_to_use if t in (prices_df.columns.tolist() if hasattr(prices_df, "columns") else [])]
    if not available:
        st.error("Keine Preisdaten für die ausgewählten Ticker vorhanden.")
        st.stop()

    # 6) Regimes an Preise anpassen
    if regimes_val is not None and hasattr(prices_df, "index") and not regimes_val.index.equals(prices_df.index):
        regimes_aligned = regimes_val.reindex(prices_df.index, method="ffill")
    else:
        regimes_aligned = regimes_val

    # 7) Backtest aufrufen
    try:
        # --- oben in der Datei sicherstellen ---
        # from risk_dashboard.utils.backtest_adapter import adapter_run_backtest
        # from risk_dashboard.ui.helpers import safe_backtest_call, render_backtest
        # from risk_dashboard.core.macro_pipeline import _fetch_and_clean_prices

        run_disabled = False

        # Widgets (einmalig)
        
        # --- Vorbereitung / Widgets (unverändert) ---
        selected_tickers_input = st.text_input("Tickers (Komma getrennt)", "NVDA,EXS1.DE,AAPL", key="selected_tickers_input")
        # ... start_date / end_date etc.
        # --- Detect ticker list changes and reset caches if needed ---
        ticker_list = parse_tickers(selected_tickers_input)  # e.g. ['NVDA','EXS1.DE','AAPL','DAX']
        ticker_list_upper = [t.upper() for t in ticker_list]

        prev_tickers = st.session_state.get("last_selected_tickers_upper")
        if prev_tickers != ticker_list_upper:
            logger.debug("Ticker list changed: %s -> %s", prev_tickers, ticker_list_upper)
            # Invalidate caches that depend on the ticker universe
            for k in ("prices_df","available_mapped","user_weights_mapped","regimes_aligned","removed_on_load","last_backtest_results_df"):
                st.session_state.pop(k, None)
            # store new value
            st.session_state["last_selected_tickers_upper"] = ticker_list_upper
            # mark that we need to (re)load prices
            st.session_state["need_price_reload"] = True
        else:
            # keep previous flag if present
            st.session_state.setdefault("need_price_reload", False)

        # --- Optional: alias map for common index names ---
        ALIAS_MAP = {
            "DAX": ["DAX", "XDAX.DE", "XUDE.DE"],
            "S&P": ["SPX", "SP500", "CSPX.L"],
            # weitere Aliase hier
        }

        def find_best_column_for_alias(alias_upper: str, cols_upper_map: dict, alias_map: dict = ALIAS_MAP):
            # 1) exact match
            if alias_upper in cols_upper_map:
                return cols_upper_map[alias_upper]

            # 2) explicit alias candidates from alias_map
            candidates = alias_map.get(alias_upper, [])
            for cand in candidates:
                if cand.upper() in cols_upper_map:
                    return cols_upper_map[cand.upper()]

            # 3) contains match (e.g., 'DAX' -> 'XDAX.DE')
            for cu, orig in cols_upper_map.items():
                if alias_upper in cu:
                    return orig

            # 4) suffix/prefix heuristics (e.g., endswith '.DE' variants)
            for cu, orig in cols_upper_map.items():
                if cu.startswith(alias_upper) or cu.endswith(alias_upper):
                    return orig

            return None

        def align_regimes_to_tickers(regimes, available_mapped):
            """
            regimes: DataFrame (index=time, columns=ticker-like) OR dict/list (custom)
            available_mapped: list of actual price column names (case sensitive)
            returns: regimes subset reindexed to available_mapped or None
            """
            if regimes is None:
                return None

            # If regimes is a DataFrame: keep only matching columns (exact match)
            if isinstance(regimes, pd.DataFrame):
                keep = [c for c in available_mapped if c in regimes.columns]
                if not keep:
                    return None
                # reindex columns in the same order as available_mapped
                return regimes.reindex(columns=keep)

            # If regimes is a dict mapping ticker->series or similar:
            if isinstance(regimes, dict):
                out = {}
                for c in available_mapped:
                    if c in regimes:
                        out[c] = regimes[c]
                    else:
                        # try uppercase match
                        for k in list(regimes.keys()):
                            if k.upper() == c.upper():
                                out[c] = regimes[k]
                                break
                return pd.DataFrame(out) if out else None

            # If regimes is a list or other structure, implement domain-specific alignment
            try:
                # fallback: try to coerce to DataFrame
                df = pd.DataFrame(regimes)
                keep = [c for c in available_mapped if c in df.columns]
                return df.reindex(columns=keep) if keep else None
            except Exception:
                logger.exception("align_regimes_to_tickers: unsupported regimes format")
                return None

        # --- Preise nur laden / aktualisieren wenn nötig ---
        def _normalize_col_map(df):
            return {c.upper(): c for c in (df.columns if df is not None else [])}

        # current cached prices
        cached_prices = st.session_state.get("prices_df")  # DataFrame or None
        cached_cols_upper = _normalize_col_map(cached_prices)

        # decide if we need a full reload or only to fetch missing tickers
        requested_upper = [t.upper() for t in ticker_list]
        missing_in_cache = [t for t in requested_upper if t not in cached_cols_upper]

        start_date = st.date_input("Startdatum", value=DEFAULT_START_STR)
        end_date = st.date_input("Enddatum", value=DEFAULT_END_STR)
        start_arg = start_date.isoformat() if start_date else None
        end_arg = end_date.isoformat() if end_date else None

        need_reload = False
        # if no cache at all -> reload
        if cached_prices is None or getattr(cached_prices, "empty", True):
            need_reload = True
        # if any requested ticker missing -> try to fetch only missing tickers
        elif missing_in_cache:
            # try to fetch only the missing tickers (safer than assuming alias matches)
            try:
                # _fetch_and_clean_prices should accept a list of tickers and return (df, removed)
                new_prices, removed_on_load = _fetch_and_clean_prices([t for t in ticker_list if t.upper() in missing_in_cache],
                                                                    start=start_arg, end=end_arg)
                # merge new_prices into cached_prices (align on index)
                if new_prices is not None and not new_prices.empty:
                    # ensure column names in new_prices match the original case mapping
                    # new_prices columns are expected to be the tickers as returned by the loader
                    if cached_prices is None or getattr(cached_prices, "empty", True):
                        merged = new_prices
                    else:
                        merged = cached_prices.join(new_prices, how="outer")
                    st.session_state["prices_df"] = merged
                    st.session_state.setdefault("removed_on_load", []).extend(removed_on_load or [])
                else:
                    # if fetch failed for missing tickers, mark for full reload
                    need_reload = True
            except Exception:
                logger.exception("Fetching missing tickers failed; will attempt full reload")
                need_reload = True

        # if flagged, do a full reload for all requested tickers
        if need_reload:
            prices_df, removed_on_load = _fetch_and_clean_prices(ticker_list, start=start_arg, end=end_arg)
            st.session_state["prices_df"] = prices_df
            st.session_state["removed_on_load"] = removed_on_load or []

        # now prepare for backtest using the (possibly updated) prices_df
        prices = st.session_state.get("prices_df")
        available = [t.upper() for t in ticker_list]  # normalized upper-case list

        st.write("DEBUG available:", available)
        st.write("DEBUG prices columns:", None if prices is None else list(prices.columns))

        # defensive checks before using prices
        if prices is None or getattr(prices, "empty", True):
            st.warning("Preisdaten sind nicht geladen. Bitte Preise laden oder Cache prüfen.")
            run_disabled = True
        else:
            # map requested tickers to actual price columns (case-insensitive)
            cols_upper_map = {c.upper(): c for c in prices.columns}
            available_mapped = []
            for t in available:
                mapped = None
                if t in cols_upper_map:
                    mapped = cols_upper_map[t]
                else:
                    mapped = find_best_column_for_alias(t, cols_upper_map)
                if mapped:
                    available_mapped.append(mapped)
                else:
                    logger.debug("Ticker %s not found in prices.columns", t)

            # --- regimes alignment (unchanged logic, but keep regimes_aligned variable) ---
            regimes = st.session_state.get("regimes")  # original regimes computed on macro_df
            regimes_aligned = None
            if regimes is not None:
                try:
                    if isinstance(regimes, pd.DataFrame):
                        keep = [c for c in available_mapped if c in regimes.columns]
                        regimes_aligned = regimes[keep] if keep else None
                    else:
                        regimes_aligned = align_regimes_to_tickers(regimes, available_mapped)
                except Exception:
                    logger.exception("Failed to align regimes")
                    regimes_aligned = None

            # --- availability check ---
            if not available_mapped:
                st.warning("Keine der ausgewählten Ticker in den Preisdaten vorhanden.")
                run_disabled = True
            else:
                # Defaults für Weights / Regimes aus session_state oder fallback
                user_weights_mapped = st.session_state.get("user_weights_mapped")
                if user_weights_mapped is None or set(user_weights_mapped.keys()) != set(available_mapped):
                    user_weights_mapped = {c: 1.0 / len(available_mapped) for c in available_mapped}
                    st.session_state["user_weights_mapped"] = user_weights_mapped

                # Verwende die lokal berechnete regimes_aligned, nicht einen anderen key
                regimes_val = regimes_aligned

                # Temporäre Debugausgaben (entfernen, wenn stabil)
                st.write("DEBUG available_mapped:", available_mapped)
                st.write("DEBUG weights:", user_weights_mapped)
                st.write("DEBUG regimes:", None if regimes_val is None else (regimes_val.head() if hasattr(regimes_val, "head") else regimes_val))

                # Sicherer UI-Aufruf (defensiv)
                # Achte darauf, dass 'prices' ein DataFrame ist und die Spalten enthält
                prices_arg = None

                # defensive checks before using prices
                run_disabled = False

                # prices kann None, DataFrame oder anderes sein
                if prices is None or (isinstance(prices, pd.DataFrame) and prices.empty):
                    st.warning("Preisdaten sind nicht geladen. Bitte Preise laden oder Cache prüfen.")
                    run_disabled = True
                    prices_arg = pd.DataFrame()
                else:
                    # defensive slicing: nur Spalten nehmen, die wirklich in prices vorhanden sind
                    if hasattr(prices, "columns"):
                        cols = [c for c in available_mapped if c in prices.columns]
                        prices_arg = prices.loc[:, cols] if cols else pd.DataFrame()
                    else:
                        # prices ist kein DataFrame (z. B. Series) — übernehme direkt
                        prices_arg = prices

                # Wenn prices_arg leer ist, deaktivieren wir den Run und informieren den Nutzer
                if isinstance(prices_arg, pd.DataFrame) and prices_arg.empty:
                    st.warning("Keine passenden Preisspalten für die ausgewählten Ticker gefunden.")
                    run_disabled = True

                # safe_backtest_call nur aufrufen, wenn nicht disabled
                result = {}
                if not run_disabled:
                    result = safe_backtest_call(
                        adapter_run_backtest,
                        args=(available_mapped,),          # tuple mit der Liste der Ticker
                        prices=prices_arg,                 # DataFrame oder leeres DF (defensiv vorbereitet)
                        weights=user_weights_mapped,       # dict ticker->weight
                        regimes=regimes_val,               # optional, falls verwendet
                        start=start_arg,
                        end=end_arg,
                        rebalance="monthly",
                        initial_cash=1_000_000,            # korrektes Keyword für deinen Adapter/Core
                        flag_key=f"{prefix}_backtest_flag",
                    )

                # Normalize None -> envelope (einheitlich)
                if result is None:
                    logger.debug("safe_backtest_call returned None")
                    result = {"ok": False, "message": "Interner Fehler: kein Ergebnis vom Backtest.", "payload": {}, "result": {}}

                # defensive Envelope handling
                resp = result or {}
                st.write("BACKTEST RESULT ENVELOPE:", resp)

                payload = resp.get("payload", {}) or {}
                res = resp.get("result", {}) or {}

                if not resp.get("ok"):
                    st.warning(resp.get("message", "Backtest fehlgeschlagen."))
                    removed = payload.get("removed") or payload.get("removed_tickers") or []
                    if removed:
                        st.warning("Entfernte Ticker: " + ", ".join(removed))
                    run_disabled = True
                else:
                    run_disabled = False
                    pv = res.get("portfolio_value")
                    metrics = res.get("metrics", {})
                    if pv is None:
                        st.warning("Kein Backtest‑Ergebnis (portfolio_value fehlt).")
                    else:
                        st.line_chart(pv)
                        st.write(metrics)
                        trades_df = pd.DataFrame(res.get("trades", []))
                        st.dataframe(trades_df)
                        if not trades_df.empty:
                            csv = trades_df.to_csv(index=False)
                            st.download_button("Export trades CSV", data=csv, file_name="trades.csv")

                # Logging (nutze die bereits initialisierten payload/res)
                logger.debug("BACKTEST CALL ARGS: available_mapped=%s weights=%s start=%s end=%s",
                            available_mapped, user_weights_mapped, start_arg, end_arg)
                logger.debug("BACKTEST RESULT ENVELOPE: %s", repr(resp)[:2000])

                pv = res.get("portfolio_value")
                metrics = res.get("metrics", {})

                logger.debug("portfolio_value type=%s shape=%s", type(pv), getattr(pv, "shape", None))
                try:
                    nunique = pv.nunique() if hasattr(pv, "nunique") else None
                    std = float(pv.std()) if hasattr(pv, "std") else None
                    logger.debug("portfolio_value nunique=%s std=%s", nunique, std)
                except Exception:
                    logger.exception("Error inspecting portfolio_value")
                # --- Defensive: konstantes Portfolio erkennen ---
                def is_constant_portfolio(pv):
                    if pv is None:
                        return True
                    if isinstance(pv, pd.Series):
                        try:
                            return pv.nunique() == 1 or float(pv.std()) == 0.0
                        except Exception:
                            return True
                    if isinstance(pv, pd.DataFrame):
                        try:
                            return all(float(pv[c].std()) == 0.0 for c in pv.columns)
                        except Exception:
                            return True
                    return True

                # --- Ergebnisbehandlung und Rendering ---
                if not res:
                    st.warning("Kein Backtest‑Ergebnis verfügbar.")
                    run_disabled = True
                else:
                    if is_constant_portfolio(pv) and metrics.get("cagr", None) in (0.0, np.float64(0.0)):
                        st.warning("Backtest lieferte keine aussagekräftigen Ergebnisse. Preisdaten, Gewichte oder Strategie prüfen.")
                        run_disabled = True
                    else:
                        removed = payload.get("removed") or payload.get("removed_tickers") or []
                        if removed:
                            st.warning("Folgende Ticker wurden entfernt (keine Preisdaten): " + ", ".join(removed))
                        # render_backtest erwartet das result-Objekt (oder das gesamte Envelope), passe an
                        render_backtest(res)
                        run_disabled = False

            # Run-Button
            if st.button("Berechnen", key="btn_backtest_requested", disabled=run_disabled):
                st.session_state["backtest_requested"] = True

                # --- Defensive check: constant portfolio detection ---
                def is_constant_portfolio(pv):
                    if pv is None:
                        return True
                    if isinstance(pv, pd.Series):
                        try:
                            return pv.nunique() == 1 or float(pv.std()) == 0.0
                        except Exception:
                            return True
                    if isinstance(pv, pd.DataFrame):
                        try:
                            return all(float(pv[c].std()) == 0.0 for c in pv.columns)
                        except Exception:
                            return True
                    return True

                # Decide whether to render
                if not payload:
                    st.warning("Kein Backtest Ergebnis verfügbar.")
                else:
                    # if portfolio is constant and metrics indicate no returns, warn and skip render
                    if is_constant_portfolio(pv) and metrics.get("cagr", None) in (0.0, np.float64(0.0)):
                        st.warning("Backtest lieferte keine aussagekräftigen Ergebnisse. Preisdaten, Gewichte oder Strategie prüfen.")
                        # optional: show debug info or a button to force render for inspection
                    else:
                        render_backtest(payload)


        # Run-Button
        if st.button("Berechnen", key="btn_etf_requested", disabled=run_disabled):
            st.session_state["backtest_requested"] = True

    except Exception:
        logger.exception("safe_backtest_call raised an exception")
        st.error("Backtest fehlgeschlagen. Details im Log.")
        bt = None

    # 8) Ergebnisse verarbeiten
    stats = None
    pv = None
    if isinstance(bt, dict) and bt:
        pv = bt.get("portfolio_value")
        metrics = bt.get("metrics", {})
        if pv is not None and not pv.empty:
            st.session_state["last_backtest_results_df"] = pv.rename("portfolio_value").reset_index()
            st.session_state["last_backtest_results_csv"] = st.session_state["last_backtest_results_df"].to_csv(index=False)
        if metrics:
            st.session_state["last_metrics"] = metrics
        try:
            stats = analyze_performance(bt)
            st.write(stats)
        except Exception:
            logger.exception("analyze_performance failed")
    else:
        st.error("Backtest lieferte keine Ergebnisse.")
        logger.debug("No backtest result to analyze (bt=%s)", bt)

    ###################################################
    from risk_dashboard.core.backtest import safe_show_backtest
    # UI Debug-Ausgaben (optional, kann entfernt werden)
    st.write("Portfolio:", portfolio)
    #st.write("Backtest:", bt)
    try:
        safe_show_backtest(bt)
    except Exception as e:
        logger.exception("safe_show_backtest failed")
        st.error(f"Fehler beim Anzeigen der Backtest‑Ergebnisse: {e}")

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

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("Set Conservative ETFs"):
            apply_preset(["aggregate_bond_etf", "government_bonds", "investment_grade_corporates", "short_term_cash"], etf_universe)
    with col_b:
        if st.button("Set Balanced ETFs"):
            apply_preset(["global_equity_etf", "aggregate_bond_etf", "small_cap"], etf_universe)
    with col_c:
        if st.button("Set Aggressive ETFs"):
            apply_preset(["global_equity_etf", "emerging_markets", "small_cap"], etf_universe)
    ####################################################################################
    with col_d:
        if st.button("Screen Top 10"):
            # Lese namespaceten asset key (prefix "etf" verwendet)
            asset_type_for_screen = st.session_state.get("etf_asset_type", "ETF")
            if asset_type_for_screen == "ETF":
                universe_meta = etf_universe
            elif asset_type_for_screen == "Stock":
                universe_meta = stock_universe
            else:
                universe_meta = st.session_state.get("combined_universe")  # bereits gebaut

            # Bulk-Preise laden (effizient)
            tickers_list = universe_meta["ticker"].tolist()
            try:
                # heavy work (after sidebar)
                price_history = fetch_price_history_bulk(tickers_list, start=None, end=None, interval="1d")
            except Exception as e:
                logger.exception("price fetch failed: %s", e)
                st.warning("Preisdaten konnten nicht geladen werden; einige UI‑Elemente sind deaktiviert.")
                price_history = None


            selected, scores = screen_and_rank(universe_meta, price_history, top_n=10)
            st.session_state["screen_selected"] = selected
            st.write("Top 10:", selected)

    ####################################################################################
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
        query = st.text_input("Kennzahl suchen", value="", key="kennzahl_query")
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
    # render_etf_tab(st.session_state)

    
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


    def save_handler(key: str, profile_obj: dict, prefix: str):
        # ss = st.session_state
        try:
            save_profile(key, profile_obj)  # deine bestehende Persistenzfunktion
            st.success(f"Profil '{profile_obj['display_name']}' gespeichert.")
            ss["profile_selected"] = key

            # path_index_choice sicher ermitteln
            #path_index_choice = ss.get("path_index_choice") or UNIVERSE_PATHS.get(
            #    ss.get(f"{prefix}_index_choice") or ss.get("index_choice")
            #)

            # Universe neu laden, falls möglich
            if path_index_choice:
                new_universe, warnings = load_etf_universe(path_index_choice)
                # optional: normalisieren new_universe = {k.upper(): v for k,v in new_universe.items()}
                ss["etf_universe"] = new_universe

                # Filtere selected_etfs auf gültige Keys
                prev = ss.get("selected_etfs", [])
                valid_etfs = [k for k in prev if k in new_universe]
                # Falls du neu hinzugefügte tickers hast, füge sie hinzu (falls verfügbar)
                # tickers muss im Scope sein oder übergeben werden; sonst weglassen
                # for t in tickers:
                #     if t in new_universe and t not in valid_etfs:
                #         valid_etfs.append(t)
                ss["selected_etfs"] = valid_etfs
                logger.debug("selected_etfs nach Reload gefiltert: %s", valid_etfs)
            else:
                logger.warning("path_index_choice nicht verfügbar; Universe nicht neu geladen")

            # Cleanup + Rerun
            ss["show_profile_editor"] = False
            ss.pop("combined_universe", None)
            ss.pop("price_data", None)
            safe_rerun()
            return

        except Exception as e:
            logger.exception("Fehler beim Speichern des Profils: %s", e)
            st.error("Fehler beim Speichern des Profils. Siehe Log.")

    # Annahme: ss = st.session_state wurde oben in profile_form_ui gesetzt
    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("Profil speichern", key=f"{prefix}_save_profile"):
            key = (profile_name or selected or "custom_profile").strip().lower().replace(" ", "_")
            allowed_instruments = ss.get("selected_etfs", [])
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

            try:
                # Persistieren
                save_profile(key, profile_obj)
                st.success(f"Profil '{profile_obj['display_name']}' gespeichert.")
                ss["profile_selected"] = key

                # 1) path_index_choice sicher ermitteln
                #path_index_choice = locals().get("path_index_choice") or ss.get("path_index_choice")
                #if not path_index_choice:
                #    index_choice = ss.get(f"{prefix}_index_choice") or ss.get("index_choice")
                #    path_index_choice = UNIVERSE_PATHS.get(index_choice)

                # 2) Neu laden, nur wenn path_index_choice vorhanden
                if path_index_choice:
                    new_universe, warnings = load_etf_universe(path_index_choice)
                    ss["etf_universe"] = new_universe

                    # Filtere alte Auswahl auf gültige Optionen
                    prev_selected = ss.get("selected_etfs", []) or []
                    valid_etfs = [k for k in prev_selected if k in new_universe]

                    # Falls neu hinzugefügte Ticker vorhanden sind: aus session oder aus allowed_instruments ableiten
                    # Variante A: neu hinzugefügte Ticker wurden in ss["new_tickers"] gespeichert
                    new_tickers = ss.get("new_tickers", [])  # optional
                    # Variante B: oder nimm allowed_instruments als Quelle
                    for t in (new_tickers or allowed_instruments):
                        if t in new_universe and t not in valid_etfs:
                            valid_etfs.append(t)

                    ss["selected_etfs"] = valid_etfs
                    logger.debug("selected_etfs nach Reload gefiltert: %s", valid_etfs)
                else:
                    logger.warning("path_index_choice nicht verfügbar; Universe nicht neu geladen")

                # 3) Cleanup + Rerun
                ss["show_profile_editor"] = False
                ss.pop("combined_universe", None)
                ss.pop("price_data", None)
                safe_rerun()
                return

            except Exception as e:
                logger.exception("Fehler beim Speichern des Profils: %s", e)
                st.error("Fehler beim Speichern des Profils. Siehe Log.")
            
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
