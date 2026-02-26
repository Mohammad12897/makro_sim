import streamlit as st
from model_runner import load_rf_model, predict
from data_loader import load_data

st.title("FX Forecast Dashboard")

df = load_data("models/fx_data_usd_eur.csv")
model = load_rf_model("models/rf_model_usd_eur.joblib")

st.line_chart(df["Close"])
