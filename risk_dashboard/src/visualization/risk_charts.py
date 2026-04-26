# risk_dashboard/src/visualization/risk_charts.py
import streamlit as st

def plot_risk_components(snap: dict):
    st.metric("Gesamt-Risiko", f"{snap['total_risk']:.2f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Inflationsrisiko", f"{snap['inflation_risk']:.2f}")
    col2.metric("Zinsrisiko", f"{snap['interest_risk']:.2f}")
    col3.metric("Wachstumsrisiko", f"{snap['growth_risk']:.2f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Arbeitsmarktrisiko", f"{snap['labor_risk']:.2f}")
    col5.metric("FX-Risiko", f"{snap['fx_risk']:.2f}")
    col6.metric("Marktstress", f"{snap['market_stress']:.2f}")