# etf_analysis.py
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from risk_dashboard.data_utils import safe_fetch
from risk_dashboard.config import DEFAULT_START_STR

# Beispiel-ETFs (anpassen)
etfs = ["SPY","IEFA","EEM","AGG","VNQ"]

# Zeitraum
start = DEFAULT_START_STR
end = None

# Daten laden
# statt direktem yf.download: benutze fetch_prices_quiet
data = safe_fetch(etfs, start=start, end=end, auto_adjust=True, threads=False)


# tÃ¤gliche Renditen
rets = data.pct_change().dropna()

# Kennzahlen
ann_factor = 252
cagr = (data.iloc[-1] / data.iloc[0]) ** (ann_factor / len(rets)) - 1
vol = rets.std() * np.sqrt(ann_factor)
sharpe = cagr / vol

summary = pd.DataFrame({
    "CAGR": cagr,
    "Volatility": vol,
    "Sharpe": sharpe
})
print(summary.sort_values("Sharpe", ascending=False))

# kumulative Rendite plot
(1 + rets).cumprod().plot(figsize=(10,6))
plt.title("Cumulative Returns")
plt.show()
plt.savefig("cumulative_returns.png", dpi=150, bbox_inches="tight")