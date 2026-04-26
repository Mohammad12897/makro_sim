import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from risk_dashboard.core.market_engine import download_etf_history, build_market_risk_factors

# 1) Prüfe, ob download_etf_history überhaupt etwas zurückgibt
raw = download_etf_history(["CSPX.L"], period="1mo")
st.write("DEBUG raw single ticker:", type(raw), raw if raw is not None else "None")

# 2) Wenn raw ein dict oder MultiIndex-DataFrame ist, zeige Struktur
if isinstance(raw, dict):
    st.write("DEBUG raw keys:", list(raw.keys()))
elif isinstance(raw, pd.DataFrame):
    st.write("DEBUG raw columns:", raw.columns.tolist())
    st.write("DEBUG raw head:", raw.head())

# 3) Teste direkten yfinance-Aufruf (falls du yfinance nutzt)
import yfinance as yf
t = yf.download("CSPX.L", period="1mo", progress=False)
st.write("DEBUG yfinance direct columns:", t.columns.tolist())
