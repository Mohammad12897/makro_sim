#src/app.py
import streamlit as st
from src.data_loader import load_macro_data
from src.risk_engine import compute_risk_score
from src.fx_integration import get_fx_forecast

st.set_page_config(page_title="Makro Risk Dashboard", layout="wide")
st.title("Makro Risk Dashboard")

tab_macro, tab_risk, tab_fx = st.tabs(["Makro-Daten", Risiko-Bewertung", "FX-Modul"])

with tab_macro:
    df = load_macro_data()
    st.subheader("Makro-Zeitreihen")
    st.line_chart(df.set_index("date")[["gdp_growth", "inflation", "interest_rate"]])
    st.line_chart(df.set_index("date")[["equity_index", "commodity_index", "vix"]])

with tab_risk:
    score, components = compute_risk_score(df)
    st.subheader("Aggregierter Risikoscore")
    st.metric("Risikoscore (Beispiel)", f"{score:.2f}")
    st.subheader("Komponenten")
    st.json({k: float(v) for k, v in components.items()})

with tab_fx:
    st.subheader("FX-Integration (USD/EUR)")
    fx_forecast = get_fx_forecast()
    st.metric("FX-Vorhersage (USD/EUR)", f"{fx_forecast:.4f}")
