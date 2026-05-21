# risk_dashboard/ui/profiles_ui.py
"""
Streamlit UI for managing portfolio profiles (presets) with validation and analysis.
"""
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from io import StringIO
import requests
import plotly.graph_objects as go
import pandas as pd

import streamlit as st
import yaml


from risk_dashboard.core.config import load_profiles, save_profile, load_etf_universe
from risk_dashboard.core.utils import resolve_components, analyze_portfolio_components, normalize_ter_value

from risk_dashboard.core.analytics import analyze_ticker
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
import pandas as pd


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

BASE_DIR = Path(__file__).resolve().parents[1]
LEX_PATH = BASE_DIR / "docs" / "lexikon.md"

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

def compute_abs_weights(df: pd.DataFrame, portfolio_value: float) -> pd.DataFrame:
    df = df.copy()
    df["abs_weight"] = df["market_value"] / portfolio_value if portfolio_value > 0 else 0.0
    return df

def compute_etf_breakdown(etf_market_value: float, holdings_df: pd.DataFrame, portfolio_value: float) -> pd.DataFrame:
    h = holdings_df.copy()
    h["abs_weight_in_portfolio"] = h["weight_in_etf"] * (etf_market_value / portfolio_value) if portfolio_value > 0 else 0.0
    return h

def load_etf_holdings(uploaded_file):
    # read
    df = pd.read_csv(uploaded_file)
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


# profiles_ui.py  (Ausschnitt / ersetze die alte render_etf_tab Implementierung)


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
    st.header("ETF vs Aktie — Absolute Gewichte (Live)")

    with st.expander("Kurzhilfe"):
        st.markdown(
            "ETF = Korb aus Wertpapieren (eigener Ticker). "
            "Absolute Gewicht = Marktwert Position / Gesamtportfolio. "
            "Bei ETFs: ETF_abs * weight_in_etf = absolutes Gewicht der Underlyings."
        )

    # 1) Portfolio Input
    uploaded = st.file_uploader("Portfolio CSV (ticker, quantity, price, market_value optional)", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Fehler beim Einlesen der Portfolio‑CSV: {e}")
            df = pd.DataFrame()
    else:
        # Fallback Demo (nur sichtbar, wenn kein Upload)
        st.info("Keine CSV hochgeladen — Beispielpositionen werden angezeigt (nur Demo).")
        df = pd.DataFrame([
            {"ticker":"CASH","quantity":100,"price":100,"market_value":10000},
            {"ticker":"ETFTECH","quantity":50,"price":400,"market_value":20000},
            {"ticker":"AAPL","quantity":0,"price":0,"market_value":70000},
        ])

    # Sicherstellen, dass market_value existiert
    if not df.empty and "market_value" not in df.columns:
        df["market_value"] = df.get("quantity", 0).fillna(0) * df.get("price", 0).fillna(0)

    # Portfolio value (automatisch oder manuell überschreiben)
    auto_portfolio_value = compute_portfolio_value(df) if not df.empty else 0.0
    portfolio_value = st.number_input("Gesamtportfolio (leer = Summe der Marktwerte)", value=float(auto_portfolio_value), format="%.2f")

    # 2) Auswahl ETFs aus Portfolio
    tickers = []
    if not df.empty and "ticker" in df.columns:
        tickers = df["ticker"].astype(str).str.upper().unique().tolist()
    selected_etfs = st.multiselect("Aus Portfolio wähle ETF(s) zur Aufschlüsselung", options=tickers)

    # 3) Holdings pro ETF (Upload, Session persistence, optional Demo)
    holdings_map: Dict[str, pd.DataFrame] = {}
    holdings_dir = Path("data/holdings")
    holdings_dir.mkdir(parents=True, exist_ok=True)

    for etf in selected_etfs:
        st.markdown(f"**Holdings für {etf}**")
        # Checkbox: Demo nur auf Anfrage
        use_demo = st.checkbox(f"Demo‑Holdings für {etf} anzeigen", key=f"demo_{etf}")

        # File uploader (persistiert in session_state und optional auf Disk)
        uploaded_h = st.file_uploader(f"Holdings CSV für {etf} (ticker, weight_in_etf)", key=f"h_{etf}")
        df_key = f"holdings_{etf}"

        if uploaded_h:
            try:
                hdf = pd.read_csv(uploaded_h)
                hdf = normalize_holdings_df(hdf)
                # persist in session
                st.session_state[df_key] = hdf
                # optional: persist to disk for reuse across reruns
                try:
                    hdf.to_csv(holdings_dir / f"{etf}.csv", index=False)
                except Exception:
                    st.info("Konnte Holdings nicht auf Disk speichern (Berechtigung/FS).")
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Holdings‑CSV für {etf}: {e}")
                hdf = st.session_state.get(df_key, pd.DataFrame())
        else:
            # kein Upload in dieser Session: lade aus session_state oder von Disk
            if df_key in st.session_state:
                hdf = st.session_state[df_key]
            else:
                disk_file = holdings_dir / f"{etf}.csv"
                if disk_file.exists():
                    try:
                        hdf = pd.read_csv(disk_file)
                        hdf = normalize_holdings_df(hdf)
                        st.session_state[df_key] = hdf
                    except Exception as e:
                        st.error(f"Fehler beim Laden der gespeicherten Holdings für {etf}: {e}")
                        hdf = pd.DataFrame()
                else:
                    hdf = pd.DataFrame()

        # Demo nur wenn keine echten Holdings vorhanden und Checkbox gesetzt
        if hdf.empty and use_demo:
            hdf = pd.DataFrame([
                {"ticker":"AAPL","weight_in_etf":0.30},
                {"ticker":"MSFT","weight_in_etf":0.30},
                {"ticker":"NVDA","weight_in_etf":0.20},
                {"ticker":"AMZN","weight_in_etf":0.20},
            ])
            st.caption("Demo‑Holdings (nur Testzwecke).")

        # Zeige kurze Vorschau oder Hinweis
        if not hdf.empty:
            st.dataframe(hdf.head(10))
        else:
            st.info("Keine Holdings geladen. Lade eine CSV hoch oder aktiviere Demo.")

        holdings_map[etf] = hdf

    # 4) Berechnen (nur bei Klick)
    if st.button("Berechnen"):
        if df.empty:
            st.error("Kein Portfolio vorhanden. Bitte Portfolio CSV hochladen.")
        else:
            df_res = compute_abs_weights(df, portfolio_value)
            df_display = df_res[["ticker","market_value","abs_weight"]].copy()
            df_display["market_value"] = df_display["market_value"].map("€{:,.2f}".format)
            df_display["abs_weight"] = (df_display["abs_weight"]*100).map("{:.2f}%".format)
            st.subheader("Positionen im Portfolio")
            st.dataframe(df_display)

            # ETF Breakdowns
            for etf in selected_etfs:
                st.subheader(f"Breakdown {etf}")
                etf_row = df[df["ticker"].astype(str).str.upper() == etf.upper()]
                if etf_row.empty:
                    st.warning(f"{etf} nicht in Portfolio gefunden. Bitte zuerst als Position hinzufügen.")
                    continue
                etf_mv = float(etf_row["market_value"].iloc[0])
                hdf = holdings_map.get(etf, pd.DataFrame())
                if hdf.empty:
                    st.warning(f"Keine Holdings für {etf} vorhanden.")
                    continue
                breakdown = compute_etf_breakdown(etf_mv, hdf, portfolio_value)
                display = breakdown.copy()
                display["weight_in_etf"] = (display["weight_in_etf"]*100).map("{:.2f}%".format)
                display["abs_weight_in_portfolio"] = (display["abs_weight_in_portfolio"]*100).map("{:.2f}%".format)
                st.dataframe(display)

            st.success("Berechnung abgeschlossen.")

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
