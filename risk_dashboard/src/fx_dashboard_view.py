# risk_dashboard/src/risk_dashboard.py

import streamlit as st
from risk_dashboard.src.fx_integration import get_fx_forecast
from risk_dashboard.src.data_loader import load_macro_data

st.title("Makro Risk Dashboard – FX Modul")

def render_fx_dashboard():
    st.subheader("FX Forecasts (USD/EUR)")

    # FX-Vorhersage
    fx_value = get_fx_forecast()
    st.metric("Vorhersage (USD/EUR)", f"{fx_value:.4f}")

    # Makro-Daten laden (falls benötigt)
    df = load_macro_data()
    st.line_chart(df.set_index("date")["equity_index"])



# risk_dashboard/src/risk_dashboard.py
from risk_dashboard.src.fx_integration import load_rf, load_lstm, predict, load_csv

def run_fx_tools():
    pass  # falls du später Funktionen einbaust