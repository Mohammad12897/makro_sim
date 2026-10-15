import pandas as pd
from risk_dashboard.data_utils import extract_ticker_from_col, fetch_prices_from_yf
from risk_dashboard.ticker_utils import normalize_ticker_simple
import re

# Test 1: MultiIndex -> flatten -> normalize
mi = pd.MultiIndex.from_tuples([('Adj Close','CSPX.L'),('Adj Close','AGGG.L')])
raw = pd.DataFrame([[1,2],[3,4]], index=pd.date_range('2026-01-01', periods=2), columns=mi)
raw_flat = raw.copy()
raw_flat.columns = ['_'.join(map(str, c)).strip() for c in raw_flat.columns]
adj = raw_flat.copy()
normalized = [normalize_ticker_simple(extract_ticker_from_col(c)) for c in adj.columns]
print("Test1 normalized:", normalized)
assert normalized == ['CSPX.L', 'AGGG.L']

# Test 2: already flattened names
raw2 = pd.DataFrame({
  'CSPX.L_Adj Close':[1,3],
  'AGGG.L_Close':[2,4]
}, index=pd.date_range('2026-01-01', periods=2))
adj2 = raw2.copy()
normalized2 = [normalize_ticker_simple(extract_ticker_from_col(c)) for c in adj2.columns]
print("Test2 normalized:", normalized2)
assert normalized2 == ['CSPX.L', 'AGGG.L']

print("Normalization tests passed")

print("-----------------------")

# lade echte Preise für die Ticker, die du in Logs hattest
df = fetch_prices_from_yf(['AGGG.L','CSPX.L','EUNL.DE','IMEU.L','IQQ0.DE','SGLN.L'], lookback_days=365)
print("cols:", list(df.columns))
print("index range:", df.index.min(), df.index.max())
assert len(df.columns) == 6

print("-----------------------")

mi = pd.MultiIndex.from_tuples([('Adj Close','CSPX.L'),('Adj Close','AGGG.L')])
raw = pd.DataFrame([[1,2],[3,4]], index=pd.date_range('2026-01-01', periods=2), columns=mi)
# simuliere pipeline: flatten -> extract -> normalize
raw_flat = raw.copy()
raw_flat.columns = ['_'.join(map(str,c)).strip() for c in raw_flat.columns]
adj = raw_flat.copy()
normalized = [normalize_ticker_simple(extract_ticker_from_col(c)) for c in adj.columns]
assert normalized == ['CSPX.L','AGGG.L']

print("-----------------------")

# Erzeuge absichtlich zwei Spalten, die nach Normalisierung gleich werden
raw3 = pd.DataFrame({
  'CLOSE_A':[1,2],
  'CLOSE_B':[3,4]
}, index=pd.date_range('2026-01-01', periods=2))
# prüfe, dass deine Funktion Duplikate erkennt und loggt
df = fetch_prices_from_yf(['CLOSE_A','CLOSE_B'])  # oder simuliere intern

print("-----------------------")

# 1. Echte Ticker 1 Jahr
from risk_dashboard.data_utils import fetch_prices_from_yf
df = fetch_prices_from_yf(['AGGG.L','CSPX.L','EUNL.DE','IMEU.L','IQQ0.DE','SGLN.L'], lookback_days=365)
print("cols:", list(df.columns))
print("index range:", df.index.min(), df.index.max())
assert set(df.columns) == {'AGGG.L','CSPX.L','EUNL.DE','IMEU.L','IQQ0.DE','SGLN.L'}
