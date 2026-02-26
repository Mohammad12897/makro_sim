import streamlit as st
from src.fx_integration import load_rf, load_lstm, predict, load_csv

st.title("Makro Risk Dashboard")

tab_macro, tab_risk, tab_fx = st.tabs(["Makro", "Risiko", "FX"])

with tab_fx:
    st.subheader("FX Forecasts (USD/EUR)")
    df = load_csv("../fx_dashboard/data/fx_data_usd_eur.csv")
    st.line_chart(df["Close"])

    model = load_rf("../fx_dashboard/models/rf_model_usd_eur.joblib")
    last_value = df["Close"].iloc[-1]
    pred = predict(model, [[last_value]])

    st.metric("Vorhersage", pred[0])
