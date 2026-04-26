# risk_dashboard/src/app.py
# $env:PYTHONPATH="C:\Projects\makro_sim"

import gradio as gr
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf


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
    ensure_date_series
)
from risk_dashboard.core.macro_loader import load_macro_data, load_macro_series
from risk_dashboard.core.scenario_engine import (
    load_base_data, 
    apply_shock, 
    SCENARIOS, 
    build_baseline_scenario, 
    build_scenario,
)

from risk_dashboard.core.fx_forecast import forecast_fx_arima, forecast_fx_prophet
from risk_dashboard.core.fx_engine import download_fx_history
from risk_dashboard.core.market_engine import download_etf_history, build_market_risk_factors
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
from risk_dashboard.core.risk_ampel import compute_risk_score
from risk_dashboard.core.regime_model import (
    classify_regime_from_score,
    build_regime_timeline,
    compute_regime_transition_matrix,
    next_regime_distribution,
)

from risk_dashboard.core.asset_packages import parse_etf_input
from risk_dashboard.ui.risk_profiles import show_risk_profiles


# macro_df: date-indexed, columns: ['gdp_growth', 'inflation', 'unemployment', 'rate']
from risk_dashboard.core.regime_hmm import fit_hmm_regimes, map_hmm_states_to_labels

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Macro Risk Dashboard", layout="wide")
st.title("Macroeconomic Risk Dashboard")

# Risikoprofile Sektion
show_risk_profiles()

AVAILABLE_ETF = [
    "CSPX.L",   # S&P 500
    "EQQQ.L",   # Nasdaq 100
    "EUNL.DE",  # MSCI World
    "IQQ0.DE",  # Quality
    "IMEU.L",   # Europe (stabiler als VEVE.L)
    "AGGG.L",   # Global Aggregate Bonds
    "IEGA.L",   # EUR Government Bonds
    "SGLN.L",   # Gold
    "PCOM.L"    # Commodities
]



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


# UI Defaults
low_defaults = ["CSPX.L", "EUNL.DE"]
med_defaults = ["IMEU.L", "IQQ0.DE"]
high_defaults = ["AGGG.L", "SGLN.L"]

# Textinputs mit eindeutigen Keys
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



# ---------------------------------------------------------
# TABS (KORRIGIERT)
# ---------------------------------------------------------
tab_macro, tab_fx, tab_scenarios, tab_risk, tab_hmm , tab_invest, tab_lexikon = st.tabs(
    ["📈 Macro Data", "💱 FX Forecast", "🧪 Szenarien", "⚠️ Risiko", "HMM-Regime", "📊 Investment", "📘 Lexikon"]
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
        help=get_definition("Makroserien")
    )

    # KORREKT: Einzelne Serie laden
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
    st.plotly_chart(fig, width="stretch")


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
        help="ARIMA = klassisches Zeitreihenmodell, Prophet = robustes Forecasting-Modell."
    )

    hist_arima = fc_arima = hist_prophet = fc_prophet = None

    if model_choice in ["ARIMA", "Both"]:
        hist_arima, fc_arima = forecast_fx_arima(steps=60)

    if model_choice in ["Prophet", "Both"]:
        hist_prophet, fc_prophet = forecast_fx_prophet(steps=60)

    fig = go.Figure()

    # -------------------------
    # ARIMA
    # -------------------------
    if model_choice in ["ARIMA", "Both"]:
        fig.add_trace(go.Scatter(
            x=hist_arima["date"], y=hist_arima["fx"],
            mode="lines", name="Historical (ARIMA)"
        ))
        fig.add_trace(go.Scatter(
            x=fc_arima["date"], y=fc_arima["fx"],
            mode="lines", name="Forecast (ARIMA)"
        ))

    # -------------------------
    # Prophet
    # -------------------------
    if model_choice in ["Prophet", "Both"]:
        fig.add_trace(go.Scatter(
            x=hist_prophet["ds"], y=hist_prophet["y"],
            mode="lines", name="Historical (Prophet)"
        ))
        fig.add_trace(go.Scatter(
            x=fc_prophet["ds"], y=fc_prophet["yhat"],
            mode="lines", name="Forecast (Prophet)"
        ))

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


    # Alle Variablen extrahieren
    variables = sorted(scenario_df["variable_Label"].unique())


    fig = go.Figure()

    variables = sorted(scenario_df["variable_Label"].unique())

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
# RISK SCORE TAB
# ---------------------------------------------------------
# Teil 3 – Risk, Regime, HMM
with tab_risk:
    st.header("Makro-Risiko-Score & Regime-Modell")

    # 1. PCA-basierter Risiko-Score (compute_risk_score_v2 liefert idealerweise 'risk_score' normiert)
    risk_score_df = compute_risk_score_v2(normalize=True, method="minmax")

    # Defensive Prüfung: mindestens eine Zeile
    if risk_score_df.empty:
        st.error("Keine Risiko-Daten verfügbar.")
        st.stop()

    # Mögliche Spalten priorisieren (falls compute_risk_score_v2 noch 'risk_score_pca' liefert)
    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    col = next((c for c in preferred_cols if c in risk_score_df.columns), None)
    if col is None:
        st.error(f"Erwartete Spalte nicht gefunden. Vorhandene Spalten: {risk_score_df.columns.tolist()}")
        st.stop()

    # Aktueller Score (float)
    latest = float(risk_score_df.iloc[-1][col])

    # Falls 'date' noch Spalte ist, sicherstellen, dass sie datetime ist
    if not isinstance(risk_score_df.index, pd.DatetimeIndex) and "date" in risk_score_df.columns:
        risk_score_df["date"] = pd.to_datetime(risk_score_df["date"], errors="coerce")
        risk_score_df = risk_score_df.set_index("date")

    # 12M-Vergleich: shift(12) nur wenn Zeitreihe mindestens 13 Einträge hat
    df_risk = risk_score_df.reset_index(drop=False)
    if col in df_risk.columns and len(df_risk) > 12:
        df_risk[f"{col}_shift12"] = df_risk[col].shift(12)
        one_year_ago = df_risk[f"{col}_shift12"].iloc[-1] if not pd.isna(df_risk[f"{col}_shift12"].iloc[-1]) else None
    else:
        one_year_ago = None

    # Anzeige
    col1, col2 = st.columns(2)
    col1.metric("Aktueller Risiko-Score", f"{latest:.3f}")
    if one_year_ago is not None:
        col2.metric("Veränderung 12M", f"{latest - one_year_ago:.3f}")
    else:
        col2.metric("Veränderung 12M", "nicht verfügbar")

    # Plot: Risiko-Score Zeitreihe (verwende die standardisierte Spalte)
    plot_df = df_risk.copy()

    # ensure date column exists
    if "date" not in plot_df.columns:
        plot_df = plot_df.reset_index().rename(columns={"index": "date"})
    plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")

    # choose column to plot
    plot_col = "risk_score" if "risk_score" in plot_df.columns else col

    # defensive checks
    st.write("DEBUG cols:", plot_df.columns.tolist())
    st.write("DEBUG head:", plot_df.head())
    if plot_df.empty or plot_col not in plot_df.columns:
        st.warning("Keine gültigen Daten für den Plot.")
    else:
        fig = px.line(plot_df, x="date", y=plot_col, title="Makro-Risiko-Score", markers=True)
        fig.update_layout(height=500, yaxis_title="Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Der PCA-basierte Risiko-Score fasst mehrere Makrovariablen zu einer einzigen Risikokomponente zusammen."
    )

    # Markov-Regime-Modell
    st.subheader("Regime-Modell (Markov)")

    # Risiko-Score-Serie als Series mit DatetimeIndex
    if not isinstance(risk_score_df.index, pd.DatetimeIndex) and "date" in risk_score_df.columns:
        risk_score_df["date"] = pd.to_datetime(risk_score_df["date"], errors="coerce")
        risk_score_df = risk_score_df.set_index("date")
    risk_score_series = risk_score_df[col]

    # Defensive Prüfung vor Zugriff auf letzte Zeile
    if risk_score_series.empty:
        st.warning("Keine Risiko-Score-Serie vorhanden.")
        st.stop()

    # Aktuelles Regime
    current_score = float(risk_score_series.iloc[-1])
    current_regime = classify_regime_from_score(current_score)
    st.metric("Aktuelles Makro-Szenario", current_regime)

    # Regime-Timeline und Transition Matrix
    regime_df = build_regime_timeline(risk_score_series)
    trans_matrix = compute_regime_transition_matrix(regime_df)

    st.subheader("Regime-Transitionsmatrix")
    st.dataframe(trans_matrix.style.format("{:.2f}"))

    # Wahrscheinlichkeit nächstes Regime
    next_dist = next_regime_distribution(current_regime, trans_matrix)
    st.subheader("Wahrscheinlichkeit nächstes Regime")
    st.bar_chart(next_dist)

    # Debug (temporär)
    st.write("DEBUG cols:", risk_score_df.columns.tolist())
    st.write("DEBUG head:", risk_score_df.head())
    st.write("DEBUG regime_df head:", regime_df.head() if not regime_df.empty else "empty")

with tab_hmm:
    st.header("HMM-Regime-Modell")

    # Stelle sicher, dass macro_df existiert (wurde in tab_macro geladen)
    try:
        macro_df  # prüft Existenz
    except NameError:
        st.error("Makro-Daten (macro_df) nicht gefunden. Bitte zuerst Macro Data laden.")
    else:
        # 1. HMM trainieren
        hmm_model, hmm_regime_df = fit_hmm_regimes(macro_df, n_states=3)

        # 2. Regime-Labels erzeugen
        hmm_regime_df, label_map, best_col = map_hmm_states_to_labels(hmm_regime_df)

        # 3. Plot
        st.subheader("HMM-Regime-Zeitverlauf")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hmm_regime_df.index,
            y=hmm_regime_df[best_col],
            mode="lines",
            name=f"{best_col}"
        ))

        # farbige Regime-Bänder
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
# INVESTMENT TAB – FINAL
# ---------------------------------------------------------
with tab_invest:
    st.header("Investition – Makro-Regime, Portfolio & Backtests")

    with st.expander("Makro-Investment-Kochrezept – Wie dieses System funktioniert", expanded=True):
        st.markdown(
            """
            ### 🧠 1. Regime erkennen
            Makrodaten → Risk Score → Low / Medium / High Risk  
            (GDP, Inflation, Arbeitslosenquote, Zinsen → PCA → Clustering)

            ### 📊 2. ETF‑Universum pro Regime auswählen
            Jedes Regime hat eigene ETF‑Typen  
            (z. B. Growth im Low‑Risk, Gold/TLT im High‑Risk)

            ### ⚙️ 3. Optimierungsmethode wählen
            - **Risk Parity** → Gewichte ∝ 1 / Volatilität  
            - **HRP** → Clustering + Risikoaufteilung (Hierarchical Risk Parity)

            ### 🧩 4. Portfolio pro Regime bauen
            Gewichte werden **pro Regime** berechnet  
            (jedes Regime hat sein eigenes Portfolio)

            ### 📈 5. Backtesten
            Historische Regime + ETF‑Daten → Equity‑Kurve  
            (zeigt, wie die Strategie in der Vergangenheit funktioniert hätte)

            ### 📉 6. Performance analysieren
            Sharpe, Volatilität, Drawdown, Heatmaps  
            (pro Regime und über alle Regime hinweg)

            ### 🔧 7. Optimieren
            ETF‑Universen, Regime‑Definitionen, Optimierungsverfahren  
            (Risk Parity vs. HRP, ETF‑Auswahl, Parameter)
            """
        )


    # Kochrezept – Verständnisanker
    with st.expander("Makro-Investment-Kochrezept – Wie dieses System funktioniert", expanded=True):
        st.markdown(
            """
            **1. Regime erkennen**  
            - Makrovariablen (GDP, Inflation, Arbeitslosenquote, Zinsen) → Risk Score  
            - PCA + Clustering → Low / Medium / High Risk Regime  

            **2. ETF-Universum pro Regime auswählen**  
            - Low Risk → Growth, Zyklisch, EM  
            - Medium Risk → Value, Quality, Short Bonds  
            - High Risk → Gold, Treasuries, MinVol, Cash  

            **3. Portfolio-Optimierung durchführen**  
            - Regelbasiert: feste Gewichte pro Regime  
            - Risk Parity: Gewichte ∝ 1 / Volatilität pro Regime  
            - HRP: Hierarchical Risk Parity – Risiko zuerst zwischen Clustern, dann innerhalb der Cluster  

            **4. Backtesten**  
            - Historische Regime + ETF-Daten (Yahoo Finance)  
            - Equity-Kurven pro Strategie  

            **5. Performance pro Regime analysieren**  
            - Sharpe Ratio, Volatilität, Drawdown  
            - Heatmaps pro Regime  

            **6. Optimieren**  
            - ETF-Universen anpassen  
            - Risk-Parity-Fenster und HRP-Struktur verfeinern  
            """
        )

    # -----------------------------------------------------
    # Prozess-Diagramm – Gesamtarchitektur des Systems
    # -----------------------------------------------------
    st.subheader("🔄 Gesamtprozess – Von Makro zu Portfolio")

    st.code(
        """
Makrodaten ──► FX-Modell ──► Risiko-Score ──► Szenario ──► Regime ──► Portfolio ──► Investment-Paket

[ Makro-Panel ]
    Inflation, Wachstum, PMI, Arbeitsmarkt

[ FX-Panel ]
    USD-Trend, FX-Volatilität

[ Risiko-Score ]
    0.0 (Risk-Off)  …  1.0 (Risk-On)

[ Szenarien ]
    Rezession, Stagflation, Soft Landing, Reflation, Boom

[ Regime ]
    Low / Medium / High Risk

[ Portfolio ]
    Risk Parity / HRP / Benchmark

[ Investment-Paket ]
    ETF-Mix, Gold/Rohstoffe, Hedge, Risiko-Budget
        """
    )

    st.markdown("---")



    # -----------------------------------------------------
    # Szenario-Framework: Risiko-Score + Szenario + Regime
    # -----------------------------------------------------
    st.subheader("📊 Makro-Risiko-Score & Szenario")

    
    # -----------------------------------------------------
    # FX- und Markt-Risikofaktoren erzeugen
    # -----------------------------------------------------
    fx_prices = download_fx_history(["DX-Y.NYB"], period="10y")
    fx_df = build_fx_risk_factors(fx_prices)

    # ETF-Daten robust laden (KEIN start+end+period Konflikt)
    etf_prices = download_etf_history(["EUNL.DE"], period="10y")


    prices_norm = normalize_price_df(etf_prices)
    

    # Debug: welche Ticker fehlen
    missing = [c for c in etf_prices.columns if c not in prices_norm.columns]
    for t in missing:
        st.warning(f"{t}: DataFrame ohne 'Close' Spalte — wird übersprungen.")

    etf_prices = prices_norm.copy()


    market_df = build_market_risk_factors(etf_prices)


    # -----------------------------------------------------
    # Risiko-Score & Szenario
    # -----------------------------------------------------
    # 1) Risiko-Score berechnen
    # Annahme: macro_df, fx_df, market_df existieren bereits
    
    # 1) Score berechnen (bereits normiert)
    risk_score_df = compute_risk_score_v2(normalize=True, method="minmax")

    # 2) Defensive Prüfungen und robustes Lesen
    if risk_score_df.empty:
        st.error("Keine Risiko-Daten verfügbar.")
        st.stop()

    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    col = next((c for c in preferred_cols if c in risk_score_df.columns), None)
    if col is None:
        st.error(f"Erwartete Spalte nicht gefunden. Vorhandene Spalten: {risk_score_df.columns.tolist()}")
        st.stop()

    latest = float(risk_score_df.iloc[-1][col])

    # 3) Szenario-Serie bauen
    scenario_df = build_scenario_series(risk_score_df)
    if scenario_df.empty:
        st.warning("scenario_df ist leer. Backtests/Plots werden nicht erstellt.")
        st.stop()

    # 4) Regime vorbereiten
    scenario_regimes = scenario_df.copy().rename(columns={"scenario": "regime"})
    scenario_regimes = ensure_date_column(scenario_regimes)

    # Optional: 'date' Spalte sicherstellen
    if "date" not in scenario_regimes.columns and isinstance(scenario_regimes.index, pd.DatetimeIndex):
        scenario_regimes = scenario_regimes.reset_index().rename(columns={"index": "date"})
    if "date" in scenario_regimes.columns:
        scenario_regimes["date"] = pd.to_datetime(scenario_regimes["date"], errors="coerce")

    # Debug
    st.write("DEBUG cols:", risk_score_df.columns.tolist())
    st.write("DEBUG head:", risk_score_df.head())
    st.write("DEBUG scenario_df head:", scenario_df.head())


    # 3) Aktuelle Werte extrahieren
    current_date = scenario_df.index[-1]
    current_risk_score = float(scenario_df["risk_score"].iloc[-1])
    current_scenario = scenario_df["scenario"].iloc[-1]

    # Anzeige
    st.metric(
        label="Aktueller Risiko-Score (0–1)",
        value=f"{current_risk_score:.2f}"
    )

    st.metric(
        label="Aktuelles Makro-Szenario",
        value=current_scenario
    )

    # Risiko-Score Zeitreihe
    fig_risk = px.line(
        scenario_df,
        y="risk_score",
        title="Risiko-Score – Zeitverlauf"
    )
    fig_risk.update_layout(height=300)
    st.plotly_chart(fig_risk, width="stretch")

    # Szenario Zeitreihe
    fig_scen = px.scatter(
        scenario_df,
        y="scenario",
        title="Makro-Szenario – Zeitverlauf",
        color="scenario"
    )
    fig_scen.update_layout(height=300)
    st.plotly_chart(fig_scen, width="stretch")

    st.markdown("---")


    # -----------------------------------------------------
    # 1) Regelbasiertes Makro-Portfolio (Investment 3.0)
    # -----------------------------------------------------
    st.markdown("---")
    st.subheader("Regelbasiertes Makro-Portfolio (Investment-Modul 3.0)")

    risk_budget = st.slider(
        "Risiko-Budget (Investitionsgrad)",
        0.0, 1.0, 1.0, 0.1,
        help="0.5 = 50% des Kapitals investiert, 50% Cash."
    )

    result = investment_recommendations_v3(risk_budget=risk_budget)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Makro-Trends & Regime")
        st.write(result["macro_trends"])
        st.write("Risk Level:", result["risk_level"])
        st.write("Regime:", result["regime"])
        st.write("Risiko-Budget:", result["risk_budget"])

    with col2:
        st.subheader("Portfolio-Gewichtung (regelbasiert)")
        st.write(result["weights"])

        st.subheader("ETF-Mapping")
        for asset, etfs in result["etf_mapping"].items():
            st.markdown(f"**{asset}**")
            for e in etfs:
                st.markdown(f"- {e}")

    st.markdown("---")
    st.subheader("Regime-basierte Handelsstrategie")
    strat = regime_based_strategy()
    st.write(f"Aktuelles Regime: **{strat['regime']}**")
    st.write("Bevorzugte Assetklassen:")
    for a in strat["preferred_assets"]:
        st.markdown(f"- {a}")

    # -----------------------------------------------------
    # 2) ETF-Backtest (Regime-basiert)
    # -----------------------------------------------------
    st.markdown("---")
    st.subheader("Backtest 2.0 mit echten ETF-Daten")

    st.info("Hinweis: Hier werden beispielhafte ETF-Ticker verwendet. Du kannst sie später anpassen.")


    ticker_map = {
        "Low Risk": ["CSPX.L", "EUNL.DE"],
        "Medium Risk": ["IMEU.L", "IQQ0.DE"],
        "High Risk": ["AGGG.L", "SGLN.L"],
    }

  
    bt_etf = backtest_etf_regime_portfolio(
        ticker_map, 
        period="10y",
        scenario_df=scenario_df,
        scenario_regimes=scenario_regimes
    )

    # Debug: zeige etf_prices und bt_etf kurz
    st.write("DEBUG etf_prices:", etf_prices)
    st.write("DEBUG bt_etf (vor Anpassung):", bt_etf)

    # Wenn bt_etf leer ist, abbrechen und Meldung zeigen
    if bt_etf is None or (hasattr(bt_etf, "empty") and bt_etf.empty):
        st.warning("Backtest liefert keine Daten (bt_etf ist leer). Plot wird nicht erstellt.")
    else:
        # Falls 'date' nicht als Spalte existiert, aber der Index ein DatetimeIndex ist:
        if "date" not in bt_etf.columns and isinstance(bt_etf.index, pd.DatetimeIndex):
            bt_etf = bt_etf.reset_index().rename(columns={"index": "date"})
            st.write("DEBUG bt_etf (nach reset_index):", bt_etf.head())

        # Falls 'date' noch fehlt, prüfen wir Alternativen oder versuchen reset_index
        if "date" not in bt_etf.columns:
            alt_date_cols = [c for c in bt_etf.columns if "date" in c.lower() or "time" in c.lower()]
            if alt_date_cols:
                bt_etf = bt_etf.rename(columns={alt_date_cols[0]: "date"})
                st.write(f"DEBUG: Umbenannt {alt_date_cols[0]} -> 'date'")
            else:
                tmp = bt_etf.reset_index()
                datetime_cols = [c for c in tmp.columns if pd.api.types.is_datetime64_any_dtype(tmp[c])]
                if datetime_cols:
                    bt_etf = tmp.rename(columns={datetime_cols[0]: "date"})
                    st.write(f"DEBUG: reset_index ergab datetime Spalte {datetime_cols[0]} -> 'date'")
                else:
                    st.error("bt_etf enthält keine Spalte 'date' und kein Datetime-Index. Plot wird nicht erstellt.")
                    st.write("DEBUG bt_etf info:", tmp.info())
                    # Abbruch: kein Plot
                    bt_etf = pd.DataFrame()  # setze leer, damit unten nichts passiert

        # Jetzt sicherstellen, dass 'equity' existiert
        if not bt_etf.empty:
            if "equity" not in bt_etf.columns:
                alt_equity = [c for c in bt_etf.columns if any(k in c.lower() for k in ("equity", "portfolio", "value", "nav"))]
                if alt_equity:
                    bt_etf = bt_etf.rename(columns={alt_equity[0]: "equity"})
                    st.write(f"DEBUG: Umbenannt {alt_equity[0]} -> 'equity'")
                else:
                    st.error("bt_etf enthält keine Spalte 'equity'. Plot wird nicht erstellt.")
                    st.write("DEBUG bt_etf columns:", bt_etf.columns.tolist())
                    bt_etf = pd.DataFrame()  # Abbruch

        # Letzte Prüfungen und Plot
        if bt_etf is None or (hasattr(bt_etf, "empty") and bt_etf.empty):
            st.warning("Nach Prüfungen ist bt_etf leer. Kein Plot.")
        else:
            bt_etf["date"] = pd.to_datetime(bt_etf["date"], errors="coerce")
            bt_etf = bt_etf.dropna(subset=["date"])
            bt_etf = bt_etf.sort_values("date").reset_index(drop=True)

            # Endgültiger Debug
            st.write("DEBUG bt_etf (final):", bt_etf.head())

            # Plot sicher erstellen (einmal)
            fig_bt2 = px.line(
                bt_etf,
                x="date",
                y="equity",
                color="regime" if "regime" in bt_etf.columns else None,
                title="Regime-basierte Equity-Kurve (ETF-Backtest)"
            )
            fig_bt2.update_layout(
                height=500,
                yaxis_title="Equity (indexiert)"
            )
            st.plotly_chart(fig_bt2, width="stretch")

    # Performance-Stats nur erstellen, wenn bt_etf valide ist
    if bt_etf is not None and not (hasattr(bt_etf, "empty") and bt_etf.empty):
        stats_etf = performance_stats(bt_etf)
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
        low_custom = st.text_input(
            "Zusätzliche ETF (kommagetrennt)",
            "",
            key="low_custom"
        )
        low_final = low_multiselect + [x.strip() for x in low_custom.split(",") if x.strip()]

    with col_mr:
        st.markdown("### Medium Risk")
        med_multiselect = st.multiselect(
            "Standard-ETF auswählen",
            AVAILABLE_ETF,
            default=["IMEU.L", "IQQ0.DE"],
            key="med_multi"
        )
        med_custom = st.text_input(
            "Zusätzliche ETF (kommagetrennt)",
            "",
            key="med_custom"
        )
        med_final = med_multiselect + [x.strip() for x in med_custom.split(",") if x.strip()]

    with col_hr:
        st.markdown("### High Risk")
        high_multiselect = st.multiselect(
            "Standard-ETF auswählen",
            AVAILABLE_ETF,
            default=["AGGG.L", "SGLN.L"],
            key="high_multi"
        )
        high_custom = st.text_input(
            "Zusätzliche ETF (kommagetrennt)",
            "",
            key="high_custom"
        )
        high_final = high_multiselect + [x.strip() for x in high_custom.split(",") if x.strip()]


    # -------------------------
    # Orchestrator: Investment-Paket
    # -------------------------
    def get_investment_package(risk_score_df, scenario_df, regime_df, generate_investment_package_fn):
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

        # aktuelle Zeilen holen (column=None erlaubt Index-Fallback)
        try:
            current_risk_row = get_latest_before(risk_score_df, "date", current_date)
        except KeyError:
            current_risk_row = get_latest_before(risk_score_df, None, current_date)

        try:
            current_scenario_row = get_latest_before(scenario_df, "date", current_date)
        except KeyError:
            current_scenario_row = get_latest_before(scenario_df, None, current_date)

        try:
            current_regime_row = get_latest_before(regime_df, "date", current_date)
        except KeyError:
            current_regime_row = get_latest_before(regime_df, None, current_date)

        # sichere Extraktion mit Fallbacks
        risk_score = float(current_risk_row.get("risk_score", current_risk_row.get("risk_score_pca", float("nan"))))
        scenario = current_scenario_row.get("scenario", current_scenario_row.get("label", None))
        regime = current_regime_row.get("regime", current_regime_row.get("label", None))

        package = generate_investment_package_fn(regime, scenario, risk_score)

        return {
            "date": current_date,
            "risk_score": risk_score,
            "scenario": scenario,
            "regime": regime,
            "package": package
        }

    # -------------------------
    # 3) Optimierungsverfahren: Risk Parity vs. HRP
    # -------------------------
    st.markdown("---")
    st.subheader("Investment-Modul 4.0/5.0 – Regime-gesteuertes Optimierungsportfolio")

    opt_method = st.selectbox(
        "Optimierungsverfahren wählen",
        ["Risk Parity", "Hierarchical Risk Parity (HRP)"]
    )

    missing_rp = []
    missing_hrp = []

    if opt_method == "Risk Parity":
        bt_opt, opt_struct, missing_rp = backtest_regime_risk_parity(
            low_final, med_final, high_final,
            period="10y",
            scenario_df=scenario_df,
            scenario_regimes=scenario_regimes
        )
        st.info("Aktiv: Regime-gesteuertes Risk-Parity-Portfolio.")
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

    # Sicherstellen, dass der Backtest Daten hat
    if bt_opt is None or bt_opt.empty:
        st.error("Backtest liefert keine Daten – keine gemeinsamen Monatsenden zwischen Returns und Regimen.")
        st.stop()

    # Robust: Datum aus bt_opt bestimmen (entweder 'date' Spalte oder DatetimeIndex)
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

    # aktuelles Regime (robust)
    if "regime" in bt_opt.columns:
        current_regime = bt_opt["regime"].iloc[-1]
    else:
        current_regime = bt_opt.iloc[-1].get("regime", None)

    current_regime_label = map_regime_to_label(current_regime)

    # Aktuelle Risiko- und Szenario-Werte via get_latest_before
    try:
        current_risk_row = get_latest_before(risk_score_df, "date", current_date)
    except KeyError:
        current_risk_row = get_latest_before(risk_score_df, None, current_date)

    try:
        current_scenario_row = get_latest_before(scenario_df, "date", current_date)
    except KeyError:
        current_scenario_row = get_latest_before(scenario_df, None, current_date)

    current_risk_score = float(current_risk_row.get("risk_score", current_risk_row.get("risk_score_pca", float("nan"))))
    current_scenario = current_scenario_row.get("scenario", None)


    # Investment-Paket erzeugen und anzeigen (ein Aufruf)
    result = get_investment_package(
        risk_score_df,
        scenario_df,
        scenario_regimes,
        lambda r, s, rs: generate_investment_package(r, s, rs, etf_universes)
    )
    
    st.subheader("📦 Investment-Paket")
    st.write("Datum:", result["date"])
    st.write("Regime:", result["regime"])
    st.write("Szenario:", result["scenario"])
    st.write("Risiko-Score:", round(result["risk_score"], 3))

    package = result["package"]

    # defensive ETF-Konvertierung einmal ausführen
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


    # Plot Equity-Kurve
    fig_opt = px.line(
        bt_opt,
        x="date" if "date" in bt_opt.columns else bt_opt.index,
        y="equity",
        color="regime" if "regime" in bt_opt.columns else None,
        title=f"{opt_method} – Regime-gesteuertes Portfolio (Equity-Kurve)"
    )
    fig_opt.update_layout(yaxis_title="Equity (indexiert)", height=500)
    st.plotly_chart(fig_opt, width="stretch", key="fig_opt")

    # Performance-Kennzahlen und Gewichte je Regime
    st.subheader(f"Performance-Kennzahlen ({opt_method}-Portfolio)")
    stats_opt = performance_stats(bt_opt)
    st.write(stats_opt)

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

    # -----------------------------------------------------
    # 4) Outperformance: Risk-Parity vs. HRP
    # -----------------------------------------------------

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
    st.write("DEBUG – RP Backtest Ergebnis (Head)2:", bt_rp.head())
    bt_hrp, hrp_struct_tmp, missing_hrp_tmp = backtest_regime_hrp(
        low_final, 
        med_final, 
        high_final, 
        period="10y",
        scenario_df=scenario_df,
        scenario_regimes=scenario_regimes
    )

    # Beispiel 1
    # robustes Datum holen
    dates_rp = ensure_date_series(bt_rp)
    dates_hrp = ensure_date_series(bt_hrp)

    # Basis-Datum wählen (längere Serie als Basis)
    base_dates = dates_rp if len(dates_rp) >= len(dates_hrp) else dates_hrp
    base_dates = base_dates.reset_index(drop=True)

    # Equity-Spalten sicher extrahieren (falls vorhanden)
    rp_equity = bt_rp["equity"].reset_index(drop=True) if "equity" in bt_rp.columns else pd.Series(dtype=float)
    hrp_equity = bt_hrp["equity"].reset_index(drop=True) if "equity" in bt_hrp.columns else pd.Series(dtype=float)

    # Truncate auf minimale Länge, um Misalignment zu vermeiden
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
    fig_out.update_layout(
        height=500,
        yaxis_title="Outperformance (HRP / Risk Parity)"
    )
    st.plotly_chart(fig_out, width="stretch", key="fig_out")

    # -----------------------------------------------------
    # 5) Regime-Transitionsmatrix
    # -----------------------------------------------------
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



    # -----------------------------------------------------
    # 5) Heatmaps: Rendite & Sharpe pro Regime
    # -----------------------------------------------------
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
