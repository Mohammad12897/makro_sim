# risk_dashboard/ui/etf_selection_ui.py
import numpy as np
import streamlit as st
import pandas as pd
from datetime import date
import time
from typing import Dict, List
import json, os, re
from risk_dashboard.core.etf_tools import get_etf_candidates_for_index, compute_etf_score_components, get_preset_weights
from risk_dashboard.utils.persistence import save_user_tickers
from risk_dashboard.core.data_loader import parse_tickers
from risk_dashboard.ui.helpers import normalize_ticker
from risk_dashboard.config import DEFAULT_START_STR
from risk_dashboard.data_utils import _sanitize_date_param, cached_download_prices, do_add_tickers,safe_rerun, analyze_callback
import uuid
import logging

    
logger = logging.getLogger(__name__)

# Auswahl der Strategie
selected_strategy = st.selectbox(
    "Strategie",
    options=["buy_and_hold", "equal_weight", "momentum", "monthly_rebalance"],
    index=0
)

# Startkapital
initial_cash = st.number_input("Startkapital", min_value=0.0, value=10000.0, step=100.0, format="%.2f")

# Optional: monatliches DCA (0 = aus)
monthly_dca = st.number_input("Monatliches DCA (0 = aus)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

def map_selected_to_pricecols(selected_list, price_cols, manual_map=None):
    manual_map = manual_map or {}
    mapped = {}
    price_cols_lower = {c.lower(): c for c in price_cols}
    for s in selected_list:
        # 1) manuelle Map prüfen
        if s in manual_map:
            pc = manual_map[s]
            mapped[s] = pc if pc in price_cols else None
            continue
        # 2) exakte Übereinstimmung
        if s in price_cols:
            mapped[s] = s
            continue
        # 3) case-insensitive exact
        if s.lower() in price_cols_lower:
            mapped[s] = price_cols_lower[s.lower()]
            continue
        # 4) Teilstring-Match (case-insensitive)
        s_low = s.lower()
        candidates = [c for c in price_cols if s_low in c.lower() or c.lower() in s_low]
        if len(candidates) == 1:
            mapped[s] = candidates[0]
            continue
        # 5) kein eindeutiges Match
        mapped[s] = None
    return mapped  

def render_etf_selection_ui(prefix: str = "etf"):
    prefix = prefix or "etf"

    asset_key = f"{prefix}_asset_type"
    stable_input_key = f"{prefix}_ticker_input"

    # Defaults sicher setzen (nur vor Widget-Erzeugung)
    st.session_state.setdefault("_ui_run_id", str(uuid.uuid4()))
    st.session_state.setdefault("_ui_seq", 0)
    st.session_state.setdefault("user_tickers", [])
    st.session_state.setdefault(asset_key, "ETF")
    st.session_state.setdefault(stable_input_key, "")

    # einmalige Initialisierung (nur Setup, keine Widgets)
    init_key = f"{prefix}_ui_initialized"
    if not st.session_state.get(init_key, False):
        st.session_state[init_key] = True
        logging.getLogger(__name__).info("etf_selection_ui initial setup done")

    def next_seq():
        st.session_state["_ui_seq"] += 1
        return st.session_state["_ui_seq"]

    # LoggerAdapter für run_id/seq
    class _Adapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = self.extra.copy()
            extra.update(kwargs.pop("extra", {}))
            kwargs["extra"] = extra
            return msg, kwargs

    log = _Adapter(logger, {"run_id": st.session_state["_ui_run_id"], "seq": 0})

    # per-asset storage keys (einmalig) — sorgt für stabile session_state-Form
    for at in ("ETF", "Stock", "Mixed"):
        st.session_state.setdefault(f"{prefix}_user_tickers_{at}", [])

    # Helper: sichere Key‑Erzeugung für Widgets (einmalig)
    def _safe_widget_key(prefix: str, name: str) -> str:
        return f"{prefix}_{re.sub(r'[^A-Za-z0-9_]', '_', str(name))}"

    # Header (Hauptbereich)
    st.header("ETF Auswahl und Explainable Scoring")

    # ---------------- Sidebar (stabile Reihenfolge und Keys) ----------------
    with st.sidebar:
        st.subheader("Portfolio Eingabe")

        # namespaced radio (stable) — MUSS vor allen anderen Widgets stehen
        asset_type = st.radio(
            "Asset Type",
            ["ETF", "Stock", "Mixed"],
            index=["ETF", "Stock", "Mixed"].index(st.session_state.get(asset_key, "ETF")),
            key=asset_key
        )
        seq = next_seq()
        log.info("asset_type selected", extra={"seq": seq, "asset_type": st.session_state.get(asset_key)})

        # Einzel‑Ticker für schnelle Analyse (stabile TextInput, nur für Analyse)
        etf_val = st.text_input(
            "Einzelticker (Analyse)",
            key=f"{prefix}_stable_input",
            placeholder="z.B. AAPL oder VWRL",
        )
        st.button("Analysieren", on_click=analyze_callback, key=f"{prefix}_analyze_button")

        st.markdown("---")
        st.info("Ticker schnell hinzufügen: benutze das Sidebar Formular (Schnell hinzufügen).")
        st.markdown("---")

        # EINDEUTIGE Selectbox für ETF‑Kontext (nur hier in Sidebar)
        log.debug("About to render index selectbox in %s with prefix=%s", __name__, prefix)
        index_choice = st.selectbox(
            "Index / Universe wählen",
            ["EURO STOXX 50", "NASDAQ 100", "Nikkei 225"],
            index=1,
            key=f"{prefix}_etf_index_choice",
        )

        # Kandidaten einmalig laden (robust)
        try:
            df_candidates = get_etf_candidates_for_index(index_choice)
            if df_candidates is None:
                df_candidates = pd.DataFrame(columns=["ticker", "name", "expense_ratio", "aum"])
        except Exception:
            log.exception("get_etf_candidates_for_index failed", extra={"seq": next_seq()})
            df_candidates = pd.DataFrame(columns=["ticker", "name", "expense_ratio", "aum"])

        if df_candidates.empty:
            st.warning("Keine vordefinierten Kandidaten für diesen Index.")
            new_etfs = st.text_input("Kommaseparierte ETFs hinzufügen (z.B. EUNL.DE, CSPX.L)", key=f"{prefix}_new_etfs")
            if st.button("Kandidaten speichern", key=f"{prefix}_save_candidates"):
                from risk_dashboard.etf_candidates import add_etf_candidates
                add_etf_candidates(index_choice, [t.strip() for t in new_etfs.split(",") if t.strip()])
                safe_rerun()

    # --- Ende Sidebar Block ---

    # Debug nach Sidebar (nur logger)
    log.debug("After sidebar; asset_type=%s stable_input=%s",
              extra={"asset_type": st.session_state.get(asset_key), "stable_input": st.session_state.get(stable_input_key)})

    # ---------------- Hauptbereich (restlicher Code) ----------------
    preset = st.selectbox(
        "Gewichtungs‑Preset",
        ["Balanced", "Conservative", "Aggressive"],
        index=0,
        key=f"{prefix}_preset_select"
    )
    weights = get_preset_weights(preset)
    st.markdown(
        f"**Aktuelles Preset:** {preset} — Gewichte: TER {weights['ter']:.0%}, "
        f"AUM {weights['aum']:.0%}, Tracking {weights['tracking']:.0%}, "
        f"Replication {weights['replication']:.0%}, Liquidity {weights['liquidity']:.0%}"
    )

    # user tickers ergänzen (falls noch nicht in df_candidates)
    for t in st.session_state.get("user_tickers", []):
        if t not in df_candidates["ticker"].values:
            df_candidates = pd.concat([df_candidates, pd.DataFrame([{"ticker": t}])], ignore_index=True)

    # Holdings import
    from risk_dashboard.core.holdings import get_holdings_for_etf

    def _safe_key(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", str(s))

    # Kandidaten / Ticker rendern (Expander pro Ticker)
    for idx, row in df_candidates.iterrows():
        ticker = row["ticker"]
        with st.expander(f"{ticker}", expanded=False):
            cols = st.columns([6, 2])
            cols[0].write(f"Ticker: **{ticker}**")
            btn_key = f"{prefix}_load_holdings_{_safe_key(ticker)}"
            if cols[1].button("Holdings laden", key=btn_key):
                df_hold = get_holdings_for_etf(ticker, api_key=st.secrets.get("HOLDINGS_API_KEY"))
                if df_hold is None or df_hold.empty:
                    st.warning("Keine Holdings gefunden.")
                else:
                    st.dataframe(df_hold)

    # user tickers in Kandidatenliste ergänzen (falls noch nicht vorhanden)
    for t in st.session_state.get("user_tickers", []):
        if t not in df_candidates["ticker"].values:
            df_candidates = pd.concat([df_candidates, pd.DataFrame([{"ticker": t}])], ignore_index=True)

    # Score‑Berechnung (robust)
    comps = []
    for _, row in df_candidates.iterrows():
        try:
            comp = compute_etf_score_components(row.to_dict())
        except Exception as e:
            log.exception("compute_etf_score_components failed for row", extra={"seq": next_seq(), "ticker": row.get("ticker"), "error": str(e)})
            comp = {
                "ter_score": 0.0,
                "aum_score": 0.0,
                "tracking_score": 0.0,
                "replication_score": 0.0,
                "liquidity_score": 0.0,
            }

        total = (weights.get("ter", 0) * comp.get("ter_score", 0) +
                 weights.get("aum", 0) * comp.get("aum_score", 0) +
                 weights.get("tracking", 0) * comp.get("tracking_score", 0) +
                 weights.get("replication", 0) * comp.get("replication_score", 0) +
                 weights.get("liquidity", 0) * comp.get("liquidity_score", 0))
        comp["total_score"] = round(total * 100, 2)
        comp["ticker"] = row.get("ticker")
        comp["name"] = row.get("name")
        comp["expense_ratio"] = row.get("expense_ratio")
        comp["aum"] = row.get("aum")
        comps.append(comp)

    if not comps:
        st.warning("Keine Kandidaten‑Scores verfügbar. Prüfe die Kandidatenliste oder die Score‑Funktionen.")
        return

    df_scores = pd.DataFrame(comps)
    if "total_score" not in df_scores.columns:
        df_scores["total_score"] = 0.0

    df_scores = df_scores.sort_values("total_score", ascending=False).reset_index(drop=True)
    st.subheader("Rangliste der Kandidaten")
    st.dataframe(df_scores[["ticker", "name", "total_score", "ter_score", "aum_score", "tracking_score", "replication_score", "liquidity_score"]], width='stretch')

    # Hinweis: accidental browser dumps removed from source.
    # If you need an example marker, keep an anonymized template in risk_dashboard/docs/edge_tabs_example.txt

    # --- Export-Button ---
    if st.button("Ergebnisse exportieren", key=f"{prefix}_export"):
        pv_df = st.session_state.get("last_backtest_results_df")
        metrics = st.session_state.get("last_metrics")

        export_dir = "risk_dashboard/export"
        os.makedirs(export_dir, exist_ok=True)

        if pv_df is not None:
            pv_df.to_csv(f"{export_dir}/backtest_results.csv", index=False)

        if metrics is not None:
            with open(f"{export_dir}/results.json", "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)

        st.success("CSV und JSON erfolgreich exportiert!")

    # --- Auto select top N / manual selection ---
    top_n = st.number_input("Top N automatisch auswählen", min_value=1, max_value=min(10, len(df_scores)), value=2, key=f"{prefix}_top_n")
    auto_select = st.checkbox("Top N automatisch auswählen", value=True, key=f"{prefix}_auto_select")
    if auto_select:
        selected = df_scores["ticker"].tolist()[:top_n]
    else:
        selected = st.multiselect("ETFs manuell auswählen", df_scores["ticker"].tolist(), default=df_scores["ticker"].tolist()[:min(2, len(df_scores))], key=f"{prefix}_manual_select")

    st.write("Ausgewählt:", selected)

    # --- Explainable Breakdown ---
    if selected:
        st.subheader("Explainable Breakdown")
        for t in selected:
            row = df_scores[df_scores["ticker"] == t].iloc[0]
            with st.expander(f"{t} — {row.get('name','')} — Score {row['total_score']}"):
                st.write(f"**Total Score:** {row['total_score']}")
                st.write(f"**TER:** {row.get('expense_ratio')} → **TER Score:** {row['ter_score']}")
                st.write(f"**AUM:** {row.get('aum')} → **AUM Score:** {row['aum_score']}")
                st.write(f"**Tracking Score:** {row['tracking_score']}")
                st.write(f"**Replication Score:** {row['replication_score']}")
                st.write(f"**Liquidity Score:** {row['liquidity_score']}")
                st.write("**Komponenten‑Gewichte:**")
                st.json(weights)

    # --- Weights override UI (optional) ---
    if st.checkbox("Gewichte manuell anpassen", key=f"{prefix}_weights_override_chk"):
        w_ter = st.slider("TER Gewicht (%)", 0, 100, int(weights.get("ter", 0.0) * 100), key=f"{prefix}_w_ter")
        w_aum = st.slider("AUM Gewicht (%)", 0, 100, int(weights.get("aum", 0.0) * 100), key=f"{prefix}_w_aum")
        w_tracking = st.slider("Tracking Gewicht (%)", 0, 100, int(weights.get("tracking", 0.0) * 100), key=f"{prefix}_w_tracking")
        w_rep = st.slider("Replication Gewicht (%)", 0, 100, int(weights.get("replication", 0.0) * 100), key=f"{prefix}_w_rep")
        w_liq = st.slider("Liquidity Gewicht (%)", 0, 100, int(weights.get("liquidity", 0.0) * 100), key=f"{prefix}_w_liq")

        total = w_ter + w_aum + w_tracking + w_rep + w_liq
        if total > 0:
            weights = {
                "ter": w_ter / total,
                "aum": w_aum / total,
                "tracking": w_tracking / total,
                "replication": w_rep / total,
                "liquidity": w_liq / total,
            }
            st.success("Gewichte aktualisiert.")
        else:
            st.error("Summe der Gewichte muss > 0 sein.")

    # --- Preise laden / prüfen (vor Backtest Widgets) ---
    from risk_dashboard.core.etl import load_etf_universe_prices

    prices_df, missing_total, sel_to_price = load_etf_universe_prices(start=DEFAULT_START_STR)
    prices_loaded = (isinstance(prices_df, pd.DataFrame) and not prices_df.empty and prices_df.shape[1] >= 1)
    controls_disabled = not prices_loaded

    # --- Manual weights sliders (per selected) ---
    if "manual_weights" not in st.session_state:
        st.session_state["manual_weights"] = {}

    for t in selected:
        slider_key = _safe_widget_key(prefix, f"slider_{t}")
        default = float(st.session_state["manual_weights"].get(t, 0.0))
        val = st.slider(f"{t} Gewicht (%)", 0.0, 100.0, value=default, key=slider_key, disabled=controls_disabled)
        st.session_state["manual_weights"][t] = float(val)

    # --- user_weights berechnen (einmalig) ---
    manual = st.session_state.get("manual_weights", {})
    user_weights = {t: float(manual.get(t, 0.0)) / 100.0 for t in selected}
    total = sum(user_weights.values())
    if selected and total <= 1e-12:
        user_weights = {t: 1.0 / len(selected) for t in selected}
    else:
        user_weights = {t: (w / total) if total > 0 else 1.0 / len(selected) for t, w in user_weights.items()}

    # --- Backtest section ---
    st.subheader("Backtest der Auswahl")
    start = st.date_input("Startdatum", value=pd.to_datetime(DEFAULT_START_STR), key=f"{prefix}_start_date", disabled=controls_disabled)
    end = st.date_input("Enddatum", value=pd.to_datetime(pd.Timestamp.today().date()), key=f"{prefix}_end_date", disabled=controls_disabled)
    rebalance = st.selectbox("Rebalancing", ["monthly", "quarterly", "yearly", "none"], index=0, key=f"{prefix}_rebalance_select", disabled=controls_disabled)

    if not prices_loaded:
        st.warning("Preisdaten konnten nicht geladen werden. Controls sind deaktiviert.")

    # Backtest Button (einmalig)
    if st.button("Backtest starten", key=f"{prefix}_run_backtest", disabled=controls_disabled):
        logger.debug("Backtest clicked: selected=%s user_weights=%s", selected, user_weights)
        if not selected:
            st.warning("Keine ETFs ausgewählt.")
        else:
            # Remappe user_weights auf price-column keys
            mapped_selected = [sel_to_price[s] for s in selected if sel_to_price.get(s)]
            if not mapped_selected:
                st.error("Keine der ausgewählten Ticker konnten auf Preisspalten gemappt werden.")
                return

            user_weights_mapped = {}
            for s, w in user_weights.items():
                pc = sel_to_price.get(s)
                if pc:
                    user_weights_mapped[pc] = user_weights_mapped.get(pc, 0.0) + float(w)
                else:
                    logger.debug("WARN: Kein Mapping für %s; wird ignoriert.", s)

            total_mapped = sum(user_weights_mapped.values())
            if total_mapped <= 1e-12:
                user_weights_mapped = {pc: 1.0 / len(mapped_selected) for pc in mapped_selected}
            else:
                user_weights_mapped = {k: v / total_mapped for k, v in user_weights_mapped.items()}

            logger.debug("user_weights_mapped=%s", user_weights_mapped)

            # sanitize start/end before download
            start_s = _sanitize_date_param(start)
            end_s = _sanitize_date_param(end)

            # call backtest runner
            from risk_dashboard.core.backtest import run_backtest_flow
            with st.spinner("Backtest läuft..."):
                result = run_backtest_flow(
                    selected=mapped_selected,
                    prices_source=prices_df,
                    weights=user_weights_mapped,
                    start=start_s,
                    end=end_s,
                    strategy=st.session_state.get(f"{prefix}_strategy", "equal"),
                    initial_cash=st.session_state.get(f"{prefix}_cash", 10000.0),
                    monthly_dca=st.session_state.get(f"{prefix}_dca", 0.0),
                    rebalance=st.session_state.get(f"{prefix}_rebalance_select", "monthly"),
                )

            # Envelope handling: only small, safe UI output
            if isinstance(result, dict) and any(k in result for k in ("ok", "payload", "result")):
                resp = result
            else:
                resp = {"ok": True, "message": None, "result": result, "payload": {}}

            st.json({k: resp.get(k) for k in ("ok", "message")})
            trades = resp.get("payload", {}).get("trades") or resp.get("result", {}).get("trades")
            if trades:
                st.dataframe(pd.DataFrame(trades).head(200))

    # End of render_etf_selection_ui
