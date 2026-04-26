# risk_dashboard/src/visualization/macro_charts.py
import streamlit as st

def plot_macro_overview(df):
    st.line_chart(df.set_index("date")[["gdp_growth", "inflation", "interest_rate"]])
    st.line_chart(df.set_index("date")[["unemployment", "oil_price", "fx_rate"]])