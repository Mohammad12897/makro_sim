# risk_dashboard/ui/etf_selection_ui.py
import streamlit as st
import pandas as pd
from datetime import date
from typing import Dict, List
import json, os
from risk_dashboard.core.etf_tools import get_etf_candidates_for_index, compute_etf_score_components, get_preset_weights, download_prices
from risk_dashboard.core.macro_pipeline import run_backtest
from risk_dashboard.ui.profiles_ui import detect_historical_regimes
from risk_dashboard.utils.persistence import load_user_tickers, save_user_tickers
from risk_dashboard.core.macro_loader import load_and_validate_macro_data
from risk_dashboard.core.data_loader import parse_tickers
from risk_dashboard.ui.helpers import normalize_ticker
from risk_dashboard.config import DEFAULT_START_STR
import logging

##################
from logging.handlers import RotatingFileHandler
import uuid

LOGFILE = os.path.join(os.path.dirname(__file__), "..", "logs", "ui_debug.log")
os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)

logger = logging.getLogger("risk_dashboard.ui.etf_selection_ui")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = RotatingFileHandler(LOGFILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s [run=%(run_id)s seq=%(seq)d] %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

###################
    
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

import time
def render_etf_selection_ui(prefix: str = "etf") -> None:

    #############################################
    # in render_etf_selection_ui(...)
    st.session_state.setdefault("_ui_run_id", str(uuid.uuid4()))
    st.session_state.setdefault("_ui_seq", 0)

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

    WATCH_KEYS = [asset_key, stable_input_key, "user_tickers", f"{prefix}_user_tickers_ETF", f"{prefix}_user_tickers_Stock"]

    def snapshot(keys):
        return {k: st.session_state.get(k) for k in keys}

    ##########################################

    asset_key = f"{prefix}_asset_type"

    # globale user tickers und asset type initialisieren
    st.session_state.setdefault("user_tickers", [])
    st.session_state.setdefault(asset_key, "ETF")

    # stable input key immer anlegen (verhindert, dass der Key beim Rerun fehlt)
    stable_input_key = f"{prefix}_ticker_input"
    st.session_state.setdefault(stable_input_key, "")

    seq = next_seq(); log.debug("stable keys set", extra={"seq": seq, "keys": list(st.session_state.keys())})

    # per-asset storage keys (einmalig) — sorgt für stabile session_state-Form
    for at in ("ETF", "Stock", "Mixed"):
        st.session_state.setdefault(f"{prefix}_user_tickers_{at}", [])

    # Header (Hauptbereich)
    st.header("ETF Auswahl und Explainable Scoring")

    # Optional: temporäre Debug-Ausgaben (entfernen, wenn stabil)
    st.write("DBG asset_key:", asset_key)
    st.write("DBG stable_input_key present:", stable_input_key in st.session_state)

    
    st.write("DBG stable_input_value:", st.session_state.get(stable_input_key))
    st.write("DBG session_state keys:", sorted(list(st.session_state.keys())))

    # ---------------- Sidebar (stabile Reihenfolge und Keys) ----------------
    with st.sidebar:
        st.subheader("Portfolio Eingabe")

        # namespaced radio (stable) — MUSS vor allen anderen Widgets stehen
        asset_type = st.radio(
            "Asset Type",
            ["ETF", "Stock", "Mixed"],
            index=["ETF", "Stock", "Mixed"].index(st.session_state[asset_key]),
            key=asset_key
        )

        seq = next_seq(); log.info("asset_type selected", extra={"seq": seq, "asset_type": st.session_state[asset_key]})

        # stable input widget (immer aufrufen)
        st.text_input("Ticker hinzufügen", key=stable_input_key, placeholder="z.B. AAPL oder VWRL")

        # stable add button (immer mit stabilem Key)
        # Annahme: next_seq(), log (LoggerAdapter) und snapshot(keys) sind definiert,
        # sowie WATCH_KEYS = [asset_key, stable_input_key, "user_tickers", f"{prefix}_user_tickers_ETF", f"{prefix}_user_tickers_Stock"]

        if st.button("Hinzufügen", key=f"{prefix}_add_button"):
            # seq + before snapshot
            seq = next_seq()
            before = snapshot(WATCH_KEYS)
            log.info("add_button pressed", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq})

            # raw_val zuerst lesen
            raw_val = st.session_state.get(stable_input_key, "") or ""
            seq = next_seq(); log.debug("stable_input read", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "raw_val": raw_val})

            # parse sicher ausführen
            try:
                parsed = parse_tickers(raw_val)
                seq = next_seq(); log.debug("parsed tickers", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "parsed": parsed})
            except Exception as e:
                seq = next_seq(); log.exception("parse_tickers failed", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq})
                st.error(f"Fehler beim Parsen der Ticker: {e}")
                parsed = []

            # apply changes
            per_asset_key = f"{prefix}_user_tickers_{st.session_state.get(asset_key,'ETF')}"
            st.session_state.setdefault(per_asset_key, [])
            for t in parsed:
                t_norm = normalize_ticker(t)
                seq = next_seq(); log.debug("processing parsed ticker", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "t_norm": t_norm})
                if t_norm and t_norm not in st.session_state[per_asset_key]:
                    st.session_state[per_asset_key].append(t_norm)
                if t_norm and t_norm not in st.session_state["user_tickers"]:
                    st.session_state["user_tickers"].append(t_norm)

            save_user_tickers(st.session_state["user_tickers"])
            st.session_state[stable_input_key] = ""

            # after snapshot + diff log
            after = snapshot(WATCH_KEYS)
            seq = next_seq(); log.info("session_state diff after add", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "before": before, "after": after})


        # Render per-asset lists in fixed order (nur aktive Asset-Liste anzeigen)
        try:
            for at in ("ETF", "Stock", "Mixed"):
                seq = next_seq(); log.debug("per-asset loop start", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "at": at})
                lst_key = f"{prefix}_user_tickers_{at}"
                items = st.session_state.get(lst_key, [])
                seq = next_seq(); log.debug("lst_key/items snapshot", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "lst_key": lst_key, "items_len": len(items) if items is not None else None})

                if at == st.session_state.get(asset_key) and items:
                    st.write("Eigene Ticker (aktuell):")
                    for t in list(items):
                        cols = st.columns([8, 1])
                        cols[0].write(t)
                        if cols[1].button("x", key=f"{prefix}_rm_{at}_{t}"):
                            seq = next_seq(); log.info("remove ticker pressed", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq, "ticker": t, "lst_key": lst_key})
                            st.session_state[lst_key].remove(t)
                            if t in st.session_state.get("user_tickers", []):
                                st.session_state["user_tickers"].remove(t)
                            save_user_tickers(st.session_state["user_tickers"])
                            st.experimental_rerun()
        except Exception:
            seq = next_seq(); log.exception("exception in per-asset loop", extra={"run_id": st.session_state["_ui_run_id"], "seq": seq})

    # Debug nach Sidebar (temporär)
    st.write("DEBUG after sidebar; asset_type:", st.session_state.get(asset_key))
    st.write("DEBUG stable_input_value:", st.session_state.get(stable_input_key))

    # ---------------- Hauptbereich (restlicher Code) ----------------
    preset = st.selectbox("Gewichtungs‑Preset", ["Balanced", "Conservative", "Aggressive"], index=0, key=f"{prefix}_preset_select")
    weights = get_preset_weights(preset)
    st.markdown(
        f"**Aktuelles Preset:** {preset} — Gewichte: TER {weights['ter']:.0%}, "
        f"AUM {weights['aum']:.0%}, Tracking {weights['tracking']:.0%}, "
        f"Replication {weights['replication']:.0%}, Liquidity {weights['liquidity']:.0%}"
    )

    index_choice = st.selectbox("Index / Universe wählen", ["EURO STOXX 50", "NASDAQ 100", "Nikkei 225"], index=1, key=f"{prefix}_index_choice")
    df_candidates = get_etf_candidates_for_index(index_choice)
    if df_candidates.empty:
        st.warning("Keine vordefinierten Kandidaten für diesen Index. Bitte konfiguriere ETF_CANDIDATES.")
        return

    # user tickers in Kandidatenliste ergänzen (falls noch nicht vorhanden)
    for t in st.session_state.get("user_tickers", []):
        if t not in df_candidates["ticker"].values:
            df_candidates = pd.concat([df_candidates, pd.DataFrame([{"ticker": t}])], ignore_index=True)

    # ... restlicher Code wie Score-Berechnung, DataFrame-Ausgabe etc.

    # Compute explainable scores using current preset weights
    # We adapt compute_etf_score_components to use preset weights by temporarily overriding PRESETS if needed.
    # For simplicity, compute components and then compute total using current weights here.
    comps = []
    for _, row in df_candidates.iterrows():
        comp = compute_etf_score_components(row.to_dict())
        # recompute total with current weights
        total = (weights["ter"] * comp["ter_score"] +
                 weights["aum"] * comp["aum_score"] +
                 weights["tracking"] * comp["tracking_score"] +
                 weights["replication"] * comp["replication_score"] +
                 weights["liquidity"] * comp["liquidity_score"])
        comp["total_score"] = round(total * 100, 2)
        comp["ticker"] = row.get("ticker")
        comp["name"] = row.get("name")
        comp["expense_ratio"] = row.get("expense_ratio")
        comp["aum"] = row.get("aum")
        comps.append(comp)

    df_scores = pd.DataFrame(comps).sort_values("total_score", ascending=False).reset_index(drop=True)
    st.subheader("Rangliste der Kandidaten")
    st.dataframe(df_scores[["ticker","name","total_score","ter_score","aum_score","tracking_score","replication_score","liquidity_score"]], width='stretch')


    # Export-Button
    if st.button("Ergebnisse exportieren"):
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

    # Auto select top N
    top_n = st.number_input("Top N automatisch auswählen", min_value=1, max_value=min(10, len(df_scores)), value=2)
    auto_select = st.checkbox("Top N automatisch auswählen", value=True)
    if auto_select:
        selected = df_scores["ticker"].tolist()[:top_n]
    else:
        selected = st.multiselect("ETFs manuell auswählen", df_scores["ticker"].tolist(), default=df_scores["ticker"].tolist()[:min(2,len(df_scores))])

    st.write("Ausgewählt:", selected)

    # Show explainable breakdown for selected ETFs
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

    # Weights override UI (optional)
    if st.checkbox("Gewichte manuell anpassen"):
        w_ter = st.slider("TER Gewicht (%)", 0, 100, int(weights["ter"]*100))
        w_aum = st.slider("AUM Gewicht (%)", 0, 100, int(weights["aum"]*100))
        w_tracking = st.slider("Tracking Gewicht (%)", 0, 100, int(weights["tracking"]*100))
        w_rep = st.slider("Replication Gewicht (%)", 0, 100, int(weights["replication"]*100))
        w_liq = st.slider("Liquidity Gewicht (%)", 0, 100, int(weights["liquidity"]*100))
        total = w_ter + w_aum + w_tracking + w_rep + w_liq
        if total > 0:
            weights = {"ter": w_ter/total, "aum": w_aum/total, "tracking": w_tracking/total, "replication": w_rep/total, "liquidity": w_liq/total}
            st.success("Gewichte aktualisiert.")
        else:
            st.error("Summe der Gewichte muss > 0 sein.")

    # Session state für manuelle Gewichte initialisieren (UI-Aufbau)
    if "manual_weights" not in st.session_state:
        st.session_state["manual_weights"] = {}

    # Slider für manuelle Anpassung (wird beim Render aus session_state initialisiert)
    for t in selected:
        default = st.session_state["manual_weights"].get(t, 0.0)
        val = st.slider(f"{t} Gewicht (%)", 0.0, 100.0, value=float(default), key=f"slider_{t}")
        st.session_state["manual_weights"][t] = val

    # user_weights aus session_state erzeugen (als Dezimalanteile)
    user_weights = {t: st.session_state["manual_weights"].get(t, 0.0) / 100.0 for t in selected}
    # Fallback: falls Summe 0 -> gleichverteilen
    if sum(user_weights.values()) == 0 and selected:
        user_weights = {t: 1.0 / len(selected) for t in selected}
    
    # Backtest section
    st.subheader("Backtest der Auswahl")
    start = st.date_input("Startdatum", value=pd.to_datetime(DEFAULT_START_STR))
    end = st.date_input("Enddatum", value=pd.Timestamp.today())
    rebalance = st.selectbox("Rebalancing", ["monthly", "quarterly", "yearly", "none"], index=0, key="etf_rebalance_select")


    # falls prices schon geladen werden kann, sonst lade Metadaten zuerst
    try:
        available_etfs = list(prices.columns)
    except NameError:
        # Fallback: statische Liste oder leere Liste bis Preise geladen sind
        available_etfs = ["NVDA", "EXS1.DE", "AAPL"]

    # --- Widgets (oben im UI) ---
    selected = st.multiselect("Wähle ETFs", options=available_etfs, default=["NVDA"])
    start = st.date_input("Startdatum", value=pd.to_datetime(DEFAULT_START_STR))
    end = st.date_input("Enddatum", value=pd.Timestamp.today())

    # statt: if prices_loaded: show controls else: hide controls
    # mache:
    # einfache Definition: geladen, wenn DataFrame nicht leer
   # oben in der Datei (Imports)
    from risk_dashboard.core.etl import load_etf_universe_prices
    from risk_dashboard.data.etf_universes import ETF_UNIVERSES
    

    # irgendwo im UI-Flow, bevor Widgets gerendert werden
    prices_df, missing_total, mapping = load_etf_universe_prices(start=DEFAULT_START_STR)

    # Preise geladen wenn DataFrame mindestens eine Spalte hat und nicht leer ist
    prices_loaded = (not prices_df.empty) and (prices_df.shape[1] >= 1)
    # strengere Variante: nur wenn keine config_keys fehlen
    # prices_loaded = (not prices_df.empty) and (len(missing_total) == 0)

    controls_disabled = not prices_loaded

    # Widgets: immer anzeigen, aber ggf. deaktiviert
    STRATEGIES = ["buy_and_hold", "equal_weight", "momentum", "monthly_rebalance"]
    default_idx = 0

    selected_strategy = st.selectbox(
        "Strategie",
        options=STRATEGIES,
        index=default_idx,
        disabled=controls_disabled
    )
    initial_cash = st.number_input(
        "Startkapital",
        min_value=0.0,
        value=10000.0,
        step=100.0,
        format="%.2f",
        disabled=controls_disabled
    )
    monthly_dca = st.number_input(
        "Monatliches DCA (0 = aus)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        format="%.2f",
        disabled=controls_disabled
    )

    if not prices_loaded:
        st.warning("Preisdaten konnten nicht geladen werden. Controls sind deaktiviert.")

    # optional: user_weights (z. B. aus session_state oder ein Widget)
    user_weights = st.session_state.get("manual_weights", {s: 1.0/len(selected) for s in selected})

    if st.button("Backtest starten"):
        logger.debug("DEBUG: selected: %s", selected)
        if not selected:
            st.warning("Keine ETFs ausgewählt.")
        else:
            with st.spinner("Lade Preise und führe Backtest aus..."):
                prices = download_prices(selected, start=str(start), end=str(end))
                if prices is None or prices.empty:
                    st.error("Keine Preisdaten gefunden für die ausgewählten ETFs.")
                else:
                    ticker_map_manual = {"CSPX.L": "EXS1.DE", "EQQQ.L": "EXS2.DE"}
                    # MultiIndex safe handling
                    if isinstance(prices.columns, pd.MultiIndex):
                        try:
                            if "close" in prices.columns.levels[1]:
                                prices = prices.xs("close", axis=1, level=1)
                            elif "adjclose" in prices.columns.levels[1]:
                                prices = prices.xs("adjclose", axis=1, level=1)
                            else:
                                prices.columns = ["_".join(map(str, c)).strip() for c in prices.columns.values]
                        except Exception:
                            prices.columns = ["_".join(map(str, c)).strip() for c in prices.columns.values]

                    price_cols = list(prices.columns)
                    sel_to_price = map_selected_to_pricecols(selected, price_cols, manual_map=ticker_map_manual)
                    logger.debug("DEBUG: sel_to_price mapping: %s", sel_to_price)

                    # mapped_selected: nur price-column keys, die existieren
                    mapped_selected = [sel_to_price[s] for s in selected if sel_to_price.get(s)]
                    if not mapped_selected:
                        st.error("Keine der ausgewählten Ticker konnten eindeutig auf Preisspalten gemappt werden.")
                        return

                    # Sicherstellen, dass user_weights existiert (Default: equal)
                    if not isinstance(user_weights, dict):
                        user_weights = {s: 1.0 / len(selected) for s in selected}

                    # Remappe user_weights auf price-column keys
                    user_weights_mapped = {}
                    for s, w in user_weights.items():
                        pc = sel_to_price.get(s)
                        if pc:
                            user_weights_mapped[pc] = user_weights_mapped.get(pc, 0.0) + float(w)
                        else:
                            logger.debug("WARN: Kein Mapping für %s; wird ignoriert.", s)

                    # Normalisieren
                    total = sum(user_weights_mapped.values()) or 1.0
                    user_weights_mapped = {k: v / total for k, v in user_weights_mapped.items()}
                    logger.debug("DEBUG: user_weights_mapped keys: %s", list(user_weights_mapped.keys()))

                    # Safety: prüfen, dass gewichtete Keys in price_cols sind
                    missing = [k for k in user_weights_mapped.keys() if k not in price_cols]
                    if missing:
                        logger.error("mapped weight keys not in prices.columns: %s", missing)
                        st.error("Interner Fehler: Gewichte konnten nicht auf Preisspalten abgebildet werden.")
                        return

                    # Backtest aufrufen mit den tatsächlich vorhandenen Spalten
                    prices_for_bt = prices.loc[:, mapped_selected]
                    res = run_backtest(
                        prices_df=prices_for_bt,
                        strategy=selected_strategy,
                        initial_cash=initial_cash,
                        monthly_dca=monthly_dca,
                        weights=user_weights_mapped if user_weights_mapped else None
                    )

                    # Ergebnis anzeigen
                    if res and isinstance(res, dict):
                        st.line_chart(res["portfolio_value"])
                        st.write(res["metrics"])
                        st.dataframe(pd.DataFrame(res.get("trades", [])))
                        csv = pd.DataFrame(res.get("trades", [])).to_csv(index=False)
                        st.download_button("Export trades CSV", data=csv, file_name="trades.csv")
                    else:
                        st.error("Backtest lieferte kein Ergebnis.")

                    # Ende des neuen Backtest‑Flows: Funktion beenden, damit alter Code nicht weiterläuft
                    return
