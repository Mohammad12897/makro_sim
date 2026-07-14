# scripts/preisdaten.py
import yfinance as yf
import pandas as pd
from pathlib import Path

tickers = ["EXS1.DE", "EXS2.DE"]
BASE_DIR = Path(__file__).resolve().parents[1] / "risk_dashboard"
out_csv = BASE_DIR / "data" / "price_data.csv"
out_csv.parent.mkdir(parents=True, exist_ok=True)
start = "2015-01-01"

print("Downloading:", tickers)
data = yf.download(tickers, start=start, threads=True)

# Extrahiere Adjusted Close mit Fallbacks
prices = None
try:
    if isinstance(data, pd.Series):
        prices = data.to_frame(name=tickers[0])
    elif isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.get_level_values(0):
            prices = data["Adj Close"]
        elif "Close" in data.columns.get_level_values(0):
            prices = data["Close"]
        else:
            raise RuntimeError("Keine geeignete Preisspalte im MultiIndex gefunden.")
    else:
        if "Adj Close" in data.columns:
            prices = data["Adj Close"]
        elif "Close" in data.columns:
            prices = data["Close"]
        else:
            raise RuntimeError("Keine geeignete Preisspalte im DataFrame gefunden.")
except Exception as e:
    print("Fehler beim Extrahieren der Preisspalte:", e)
    raise

# Sicherstellen, dass es ein DataFrame ist
if isinstance(prices, pd.Series):
    prices = prices.to_frame()

prices.index = pd.to_datetime(prices.index)
prices.sort_index(inplace=True)

# Debug-Ausgabe
print("Downloaded prices shape:", getattr(prices, "shape", None))
print("Columns:", list(prices.columns)[:20])

# Speichern
prices.to_csv(out_csv)
print("Saved price_data to", out_csv)
