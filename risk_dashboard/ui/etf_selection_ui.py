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
import logging
    
logger = logging.getLogger(__name__)

def render_etf_selection_ui():
    """
    Explainable ETF selection UI with presets and Top-N auto-select.
    """
    st.header("ETF Auswahl und Explainable Scoring")

    # Sidebar / Portfolio Eingabe: Ticker hinzufügen
    if "user_tickers" not in st.session_state:
        st.session_state.user_tickers = []

    with st.sidebar:
        st.subheader("Portfolio Eingabe")
        # Eingabefeld
        new_ticker = st.text_input("Ticker hinzufügen", value="", placeholder="z.B. AAPL oder VWRL")

        # sichere Defaults
        DEFAULT_START = "2016-01-01"
        DEFAULT_END = date.today().isoformat()

        # Normalisierung: akzeptiere Liste, Dict oder String
        # parsed_tickers ist jetzt immer eine Liste
        parsed_tickers = parse_tickers(new_ticker)
        st.write("Parsed tickers:", parsed_tickers)

        # Preise laden (immer Liste übergeben)
        from risk_dashboard.ui.profiles_ui import load_price_data
        prices = load_price_data(parsed_tickers)

        # Hinzufügen-Button: validiere mit download_prices und arbeite mit der Liste
        if st.button("Hinzufügen"):
            t = new_ticker.strip().upper()
            if t:
                if t in st.session_state.user_tickers:
                    st.warning(f"{t} ist bereits in der Liste.")
                else:
                    # Validierung: kurze Preisanfrage mit einer Liste
                    test_prices = download_prices([t], start=DEFAULT_START, end=DEFAULT_END)
                    if test_prices is None or test_prices.empty:
                        st.error(f"Ticker {t} ist ungültig oder liefert keine Daten.")
                    else:
                        st.session_state.user_tickers.append(t)
                        save_user_tickers(st.session_state.user_tickers)
                        st.success(f"{t} hinzugefügt.")

        # Anzeige und Entfernen
        if st.session_state.user_tickers:
            st.write("Eigene Ticker:")
            for t in list(st.session_state.user_tickers):
                cols = st.columns([8,1])
                cols[0].write(t)
                if cols[1].button("x", key=f"rm_{t}"):
                    st.session_state.user_tickers.remove(t)
                    save_user_tickers(st.session_state.user_tickers)
                    st.experimental_rerun()

    # Preset selection
    preset = st.selectbox("Gewichtungs‑Preset", ["Balanced", "Conservative", "Aggressive"], index=0, key="etf_preset_select")
    weights = get_preset_weights(preset)

    st.markdown(f"**Aktuelles Preset:** {preset} — Gewichte: TER {weights['ter']:.0%}, AUM {weights['aum']:.0%}, Tracking {weights['tracking']:.0%}, Replication {weights['replication']:.0%}, Liquidity {weights['liquidity']:.0%}")

    # Step: choose index/universe
    index_choice = st.selectbox("Index / Universe wählen", ["EURO STOXX 50", "NASDAQ 100", "Nikkei 225"], index=1, key="etf_index_choice")

    # Load candidates
    df_candidates = get_etf_candidates_for_index(index_choice)
    if df_candidates.empty:
        st.warning("Keine vordefinierten Kandidaten für diesen Index. Bitte konfiguriere ETF_CANDIDATES.")
        return

    
    # df_candidates = get_etf_candidates_for_index(index_choice)  # bestehend
    # Füge user tickers als einfache Zeilen hinzu (falls noch nicht vorhanden)
    for t in st.session_state.get("user_tickers", []):
        if t not in df_candidates["ticker"].astype(str).tolist():
            df_candidates = pd.concat([df_candidates, pd.DataFrame([{
                "ticker": t,
                "name": t,
                "domicile": None,
                "expense_ratio": None,
                "aum": None,
                "replication": None
            }])], ignore_index=True)

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
    start = st.date_input("Startdatum", value=pd.to_datetime("2018-01-01"))
    end = st.date_input("Enddatum", value=pd.Timestamp.today())
    rebalance = st.selectbox("Rebalancing", ["monthly", "quarterly", "yearly", "none"], index=0, key="etf_rebalance_select")


    if st.button("Backtest starten"):
        logger.debug("DEBUG: selected: %s", selected)
        if not selected:
            st.warning("Keine ETFs ausgewählt.")
        else:
            with st.spinner("Lade Preise und führe Backtest aus..."):
                prices = download_prices(selected, start=str(start), end=str(end))
                if prices is None or prices.empty:
                    st.error("Keine Preisdaten gefunden für die ausgewählten ETFs.")
                    return

                # --- Mapping selected -> price columns (automatisch + manuelle Ergänzung) ---
                ticker_map_manual = {"CSPX.L": "EXS1.DE", "EQQQ.L": "EXS2.DE"}  # passe an

                def map_selected_to_pricecols(selected_list, price_cols, manual_map=None):
                    manual_map = manual_map or {}
                    mapped = {}
                    for s in selected_list:
                        # 1. manuelle Map prüfen
                        if s in manual_map:
                            pc = manual_map[s]
                            if pc in price_cols:
                                mapped[s] = pc
                                continue
                        # 2. exakte Übereinstimmung
                        if s in price_cols:
                            mapped[s] = s
                            continue
                        # 3. Teilstring-Match (case-insensitive)
                        s_low = s.lower()
                        candidates = [c for c in price_cols if s_low in c.lower() or c.lower() in s_low]
                        if len(candidates) == 1:
                            mapped[s] = candidates[0]
                            continue
                        # 4. kein eindeutiges Match
                        mapped[s] = None
                    return mapped

                # Falls prices MultiIndex-Spalten hat: flattenen / close auswählen
                if isinstance(prices.columns, pd.MultiIndex):
                    # Versuch: 'close' Ebene extrahieren, sonst flatten
                    try:
                        if 'close' in prices.columns.levels[1]:
                            prices = prices.xs('close', axis=1, level=1)
                        elif 'adjclose' in prices.columns.levels[1]:
                            prices = prices.xs('adjclose', axis=1, level=1)
                        else:
                            prices.columns = ['_'.join(map(str, c)).strip() for c in prices.columns.values]
                    except Exception:
                        prices.columns = ['_'.join(map(str, c)).strip() for c in prices.columns.values]

                price_cols = list(prices.columns)
                sel_to_price = map_selected_to_pricecols(selected, price_cols, ticker_map_manual)
                logger.debug("DEBUG: sel_to_price mapping: %s", sel_to_price)

                # Filter nur die, die gemappt wurden
                mapped_selected = [sel_to_price[s] for s in selected if sel_to_price.get(s)]
                if not mapped_selected:
                    st.error("Keine der ausgewählten Ticker konnten auf Preisspalten gemappt werden.")
                    return

                # --- Remappe user_weights (keys: selected) auf price-column keys ---
                # user_weights muss vorher existieren (z. B. aus session_state oder Default-Gewichten)
                user_weights_mapped = {}
                for s, w in user_weights.items():
                    pc = sel_to_price.get(s)
                    if pc:
                        user_weights_mapped[pc] = user_weights_mapped.get(pc, 0.0) + w
                    else:
                        logger.debug(f"WARN: Kein Mapping für {s}; wird ignoriert.")

                # Normalisieren (sicherstellen)
                total = sum(user_weights_mapped.values()) or 1.0
                user_weights_mapped = {k: v/total for k, v in user_weights_mapped.items()}
                logger.debug("DEBUG: user_weights_mapped keys: %s", list(user_weights_mapped.keys()))
                # --- Ende Mapping Block ---

                missing = [k for k in user_weights_mapped.keys() if k not in price_cols]
                if missing:
                    logger.debug("ERROR: mapped weight keys not in prices.columns:", missing)
                    st.error("Interner Fehler: Gewichte konnten nicht auf Preisspalten abgebildet werden.")
                    return

                # Regimes
                macro_df = load_and_validate_macro_data()
                regimes = detect_historical_regimes(macro_df) if macro_df is not None else None
                if regimes is not None and regimes.empty:
                    logger.debug("WARN: regimes empty — skipping regime-dependent logic")

                from risk_dashboard.utils.session_helpers import maybe_run_backtest
                from risk_dashboard.utils.backtest_adapter import adapter_run_backtest

                logger.debug("DEBUG: maybe_run_backtest from: %s", maybe_run_backtest.__module__)
                logger.debug("DEBUG: final check - prices columns sample: %s", list(prices.columns)[:20])
                logger.debug("DEBUG: final check - user_weights_mapped keys: %s", list(user_weights_mapped.keys()))


                # 1) Erzeuge portfolio_or_tickers aus der aktuellen Auswahl und dem Mapping
                # Verwende nur die ausgewählten Ticker und mappe sie auf price columns
                mapped_selected = [sel_to_price[s] for s in selected if sel_to_price.get(s)]
                # Falls du user_weights_mapped bereits berechnet hast, nutze dessen Keys
                if mapped_selected:
                    portfolio_or_tickers = mapped_selected  # einfache Liste der price-column keys
                else:
                    portfolio_or_tickers = []

                # 2) Validierungen
                if not portfolio_or_tickers:
                    st.error("Keine der ausgewählten Ticker konnten auf Preisspalten gemappt werden.")
                    res = {}
                elif prices is None or (hasattr(prices, "empty") and prices.empty):
                    st.error("Preisdaten fehlen.")
                    res = {}
                elif regimes is None or (hasattr(regimes, "empty") and regimes.empty):
                    st.error("Regime‑Daten fehlen.")
                    res = {}
                else:
                    # Optional: prüfe Zeitüberlappung zwischen prices.index und regimes.index
                    try:
                        if hasattr(prices, "index") and hasattr(regimes, "index"):
                            overlap = prices.index.intersection(regimes.index)
                            if overlap.empty:
                                st.warning("Keine Zeitüberlappung zwischen Preisdaten und Regime‑Daten. Prüfe Daten.")
                    except Exception:
                        logger.debug("WARN: konnte Index‑Overlap nicht prüfen")

                    from risk_dashboard.ui.helpers import safe_backtest_call, render_backtest

                    # --- Vorbereitung: sichere Defaults und Variablen ---
                    # Erwartet: Du hast irgendwo oben Widgets wie:
                    # selected_tickers_input = st.text_input("Tickers (Komma getrennt)", "NVDA,EXS1.DE,AAPL")
                    # start_date_input = st.date_input("Startdatum", value=None)   # optional
                    # end_date_input = st.date_input("Enddatum", value=None)       # optional
                    # user_weights_mapped = {...}  # optional, sonst None
                    # prices_subset = <DataFrame mit Preisdaten>  # muss vorher geladen werden
                    # regimes = <Series/DataFrame>  # optional

                    # sichere Initialisierung
                    run_disabled = False

                    # parse selected tickers (falls du ein Textfeld benutzt)
                    selected_tickers_input = globals().get("selected_tickers_input", None)
                    if selected_tickers_input:
                        available = [t.strip() for t in selected_tickers_input.split(",") if t.strip()]
                    else:
                        # falls 'available' bereits gesetzt ist (z. B. aus einer MultiSelect), benutze es
                        available = globals().get("available", [])

                    # Start / End sicher erzeugen (None bleibt None)
                    start_date_input = globals().get("start_date_input", None)
                    end_date_input = globals().get("end_date_input", None)
                    start_arg = start_date_input.isoformat() if start_date_input is not None else None
                    end_arg = end_date_input.isoformat() if end_date_input is not None else None

                    # Weights mapping: falls vorhanden, sonst None
                    user_weights_mapped = globals().get("user_weights_mapped", None)

                    # prices und regimes: sichere Referenzen
                    prices = globals().get("prices", None)   # oder 'prices_df' je nach Datei
                    regimes_val = globals().get("regimes", None)

                    # --- Filter available gegen prices.columns, um KeyError zu vermeiden ---
                    if prices is not None:
                        available = [t for t in available if t in prices.columns]

                    if not available:
                        st.warning("Keine der ausgewählten Ticker in den Preisdaten vorhanden.")
                        run_disabled = True
                    else:
                        # --- Sicherer Aufruf des Adapters via safe_backtest_call ---
                        result = safe_backtest_call(
                            adapter_run_backtest,
                            available,                                # positional: portfolio_or_tickers (Liste ist ok)
                            prices=prices[available] if prices is not None else None,
                            weights=user_weights_mapped,              # kann None sein
                            regimes=regimes_val,                      # optional
                            start=start_arg,
                            end=end_arg,
                            rebalance="monthly",                      # oder rebalance_freq="M" je nach Adapter
                            initial_capital=1_000_000,
                            flag_key="backtest_call"
                        ) or {}

                        # --- Ergebnis prüfen und anzeigen ---
                        if not result.get("ok"):
                            st.warning(result.get("message", "Backtest fehlgeschlagen."))
                            run_disabled = True
                        else:
                            run_disabled = False
                            bt = result["result"]
                            removed = bt.get("removed_tickers", [])
                            if removed:
                                st.warning("Entfernte Ticker: " + ", ".join(removed))
                            render_backtest(bt)

                    # Run-Button
                    if st.button("Berechnen", disabled=run_disabled):
                        # optional: setze ein SessionState-Flag oder trigger einen erneuten Aufruf
                        st.session_state["backtest_requested"] = True


                # --- Robust: Ergebnisse anzeigen, session_state updaten und Rerun-Fallback ---
                pv = res.get("portfolio_value") if isinstance(res, dict) else None
                metrics = res.get("metrics", {}) if isinstance(res, dict) else {}
                wdf = res.get("weights_over_time") if isinstance(res, dict) else None

                # Debug (Terminal)
                logger.debug("DEBUG: res type: %s", type(res))
                logger.debug("DEBUG: pv type/shape: %s  %s", type(pv), getattr(pv, "shape", None))
                logger.debug("DEBUG: wdf type/shape: %s %s ", type(wdf), getattr(wdf, "shape", None))

                # Wenn wdf vorhanden: Tabelle zeigen und session_state updaten (Slider erwarten 0-100)
                if wdf is not None and hasattr(wdf, "empty") and not wdf.empty:
                    st.subheader("Gewichte über Zeit")
                    st.dataframe(wdf.fillna(0).round(4))
                    last_weights = wdf.iloc[-1].to_dict()
                    s = sum(last_weights.values()) or 1.0
                    last_weights = {k: (v / s) * 100 for k, v in last_weights.items()}
                    st.session_state["manual_weights"] = last_weights
                else:
                    st.write("Keine Rebalancing‑Schnappschüsse vorhanden.")

                # Chart und Kennzahlen
                if pv is None or (hasattr(pv, "empty") and pv.empty):
                    st.error("Backtest lieferte keine Portfolio‑Zeitreihe.")
                else:
                    st.subheader("Kumulative Performance")
                    try:
                        #st.line_chart((pv / pv.iloc[0]).fillna(method="ffill"))
                        st.line_chart((pv / pv.iloc[0]).ffill())
                    except Exception as e:
                        logger.debug("WARN: line_chart failed:", e)
                        #st.write((pv / pv.iloc[0]).fillna(method="ffill"))
                        st.write((pv / pv.iloc[0]).ffill())

                st.subheader("Kennzahlen")
                st.json(metrics)
                # Ende Block