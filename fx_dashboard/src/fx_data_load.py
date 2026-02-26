#Abschnitt 1 — Echte FX‑Daten laden (Yahoo Finance)
!pip install yfinance

import yfinance as yf
import pandas as pd

pairs = {
    "usd_eur": "EURUSD=X",
    "usd_gbp": "GBPUSD=X",
    "usd_jpy": "JPY=X"
}

df = pd.DataFrame()

for col, ticker in pairs.items():
    df[col] = yf.download(ticker, start="2015-01-01")["Close"]

df = df.dropna()
df.head()
