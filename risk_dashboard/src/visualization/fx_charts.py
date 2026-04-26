# risk_dashboard/src/visualization/fx_charts.py
import streamlit as st
import pandas as pd
from risk_dashboard.src.core.utils import get_data_path

def plot_fx_history():
    data_path = get_data_path()
    df = pd.read_csv(data_path / "fx_data_usd_eur.csv")
    df["date"] = pd.to_datetime(df["date"])
    st.line_chart(df.set_index("date")[["Close"]])