# risk_dashboard/ui/profiles_ui.py
"""
Streamlit UI for managing portfolio profiles (presets) with validation and analysis.
"""
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import plotly.graph_objects as go
import pandas as pd

import streamlit as st
import yaml


from risk_dashboard.core.config import load_profiles, save_profile, load_etf_universe
from risk_dashboard.core.utils import resolve_components, analyze_portfolio_components, normalize_ter_value

BASE_DIR = Path(__file__).resolve().parents[1]
LEX_PATH = BASE_DIR / "docs" / "lexikon.md"

TOOLTIPS = {
    "profile_name": "Name des Profils, z. B. Conservative, Balanced, Aggressive.",
    "category": "Basis-Risikokategorie; fÃ¼llt empfohlene Standardwerte vor.",
    "equity_pct": "Anteil Aktien am Portfolio in Prozent.",
    "bond_pct": "Anteil Anleihen am Portfolio in Prozent.",
    "cash_pct": "LiquiditÃ¤tsreserve in Prozent.",
    "target_annual_return_pct": "Erwartete durchschnittliche Jahresrendite (SchÃ¤tzwert).",
    "max_drawdown_pct": "Maximal tolerierter Verlust vom Peak (z. B. 20 fÃ¼r 20%).",
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
        st.warning(f"Preset enthÃ¤lt nicht verfÃ¼gbare ETFs: {', '.join(missing)}")
    st.session_state.selected_etfs = [k for k in keys if k in etf_universe]

def profile_form_ui() -> None:
    _init_session_state_defaults()
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
        if st.button("Mit Kategorie-Defaults Ã¼berschreiben"):
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
        st.warning("Einige voreingestellte Instrumente sind im aktuellen ETFâ€‘Universe nicht vorhanden: " + ", ".join(missing_defaults) + ". Bitte wÃ¤hle Alternativen oder ergÃ¤nze das etf_universe.yaml.")

    if not st.session_state.selected_etfs and default_etfs:
        st.session_state.selected_etfs = default_etfs.copy()

    st.markdown("**Erlaubte ETFs / Instrumente**")
    selected_etfs = st.multiselect("WÃ¤hle erlaubte ETFs (optional)", options=list(etf_options.keys()), format_func=lambda k: etf_options.get(k, k), default=st.session_state.selected_etfs, help="WÃ¤hle ETFs aus dem vordefinierten Universe. Du kannst eigene Keys verwenden.")
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

    st.markdown(f"### ðŸ” Automatisch erkanntes Risiko: **{auto_risk}**")

    fig = go.Figure(go.Indicator(mode="gauge+number", value=portfolio_vol, title={"text": "Risiko-Thermometer"}, gauge={"axis": {"range": [0, 20]}, "bar": {"color": "red"}, "steps": [{"range": [0, 6], "color": "lightgreen"}, {"range": [6, 12], "color": "yellow"}, {"range": [12, 20], "color": "orange"}],},))
    st.plotly_chart(fig, width='stretch')

    with st.expander("AusgewÃ¤hlte Instrumente und Paketâ€‘Details"):
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

    with st.expander("Analyse Panel"):
        # TER-Fix + Warnschwellen: ter_threshold_warn=0.01 (1%), herfindahl_warn=0.15
        analyze_portfolio_components(etf_universe, resolved_holdings, eq, bd, cs, vol_map, ter_threshold_warn=0.01, herfindahl_warn=0.15)

    st.markdown("**Erlaubte Instrumente / AusschlÃ¼sse (alternativ)**")
    allowed_text = st.text_area("Allowed instruments (Komma-getrennt)", value=",".join(st.session_state.selected_etfs) if st.session_state.selected_etfs else ",".join(defaults.get("allowed_instruments", [])), help=TOOLTIPS["allowed_instruments"])

    st.markdown("### ðŸ”— AbhÃ¤ngigkeiten & gÃ¼ltige Eingaben")
    valid_keys = list(etf_universe.keys())
    st.markdown("**GÃ¼ltige ETF-Keys aus dem Universe:**")
    if valid_keys:
        st.code(", ".join(valid_keys))
    else:
        st.code("Keine ETFs im Universe definiert.")

    recommended_low = ["aggregate_bond_etf", "government_bonds", "investment_grade_corporates", "short_term_cash"]
    recommended_medium = ["global_equity_etf", "aggregate_bond_etf", "small_cap"]
    recommended_high = ["global_equity_etf", "emerging_markets", "small_cap"]

    st.markdown("**Empfohlene zusÃ¤tzliche ETFs pro Risikoprofil:**")
    st.info(f"**Low Risk:** {', '.join(recommended_low)}  \n**Medium Risk:** {', '.join(recommended_medium)}  \n**High Risk:** {', '.join(recommended_high)}")

    def check_invalid(user_list):
        return [x for x in user_list if x not in valid_keys]

    if check_invalid(recommended_low) or check_invalid(recommended_medium) or check_invalid(recommended_high):
        st.warning("Einige empfohlene Keys existieren nicht im Universe. Bitte etf_universe.yaml prÃ¼fen/erweitern.")

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
        if selected != "<Neu>" and st.button("Profil lÃ¶schen"):
            cfg = load_profiles()
            profiles = cfg.get("profiles", {})
            if selected in profiles:
                profiles.pop(selected)
                cfg["profiles"] = profiles
                cfg_path = BASE_DIR / "config" / "profiles.yaml"
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                with cfg_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
                st.success(f"Profil '{selected}' gelÃ¶scht.")
                st.session_state.profile_selected = "<Neu>"
                st.session_state.selected_etfs = []

    st.markdown("---")
    st.info("Tipp: WÃ¤hle ein Risikoprofil (Low/Medium/High) um empfohlene Standardwerte zu laden. Nutze Auto-normalize, damit Equity+Bonds+Cash automatisch 100% ergeben.")

    with st.expander("Kurzlexikon und Quickstart"):
        if LEX_PATH.exists():
            st.markdown(LEX_PATH.read_text(encoding="utf-8"))
        else:
            st.write("Lexikon nicht gefunden. Bitte lege docs/lexikon.md an.")

