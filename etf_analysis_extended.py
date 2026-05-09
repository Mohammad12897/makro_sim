# etf_analysis_extended.py
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# robustes Styling: versuche seaborn, sonst fallback auf matplotlib default
try:
    import seaborn as sns
    sns.set_style("darkgrid")
except Exception:
    try:
        plt.style.use("seaborn")
    except Exception:
        # fallback: matplotlib default style
        pass


# === Konfiguration ===
ETFS = ["SPY","IEFA","EEM","AGG","VNQ"]   # passe hier deine Liste an
START = "2016-01-01"
ANN_FACTOR = 252
REBALANCE_FREQ = "YE"  # 'YE' = yearly; alternatives: 'Q' quarterly, 'M' monthly

OUT_DIR = "."  # Arbeitsverzeichnis (C:/Projects/makro_sim wenn dort ausgefÃƒÂ¼hrt)

# === Hilfsfunktionen ===
def annualized_cagr(series):
    # series: price series (pd.Series) mit tÃƒÂ¤glicher Frequenz
    n_days = len(series) - 1
    if n_days <= 0:
        return np.nan
    total_return = series.iloc[-1] / series.iloc[0]
    years = n_days / ANN_FACTOR
    return total_return ** (1.0 / years) - 1.0

def max_drawdown(cum_returns):
    peak = cum_returns.cummax()
    dd = (cum_returns / peak) - 1.0
    return dd.min()

def compute_total_return(prices, dividends):
    # prices: DataFrame of Adj Close; dividends: DataFrame of dividends (same columns)
    # We compute total return by building a price series that reinvests dividends at close price on ex-date.
    # Simpler approach: use adjusted close (auto_adjust=True) which already reflects dividends.
    # But to be explicit, we will rely on adjusted close from yfinance (auto_adjust=True).
    return prices  # adjusted close already includes dividends

# === Daten laden ===
print("Lade Daten...")
data = yf.download(ETFS, start=START, auto_adjust=True, actions=True, progress=False)
if ("Close" in data.columns.levels[0]) if isinstance(data.columns, pd.MultiIndex) else False:
    prices = data["Close"]
else:
    # yfinance sometimes returns single-level columns when single ticker; normalize
    prices = data["Close"] if "Close" in data else data

# Sicherstellen: DataFrame mit Spalten = ETFS
prices = prices[ETFS].dropna(how="all")

# tÃƒÂ¤gliche Renditen
rets = prices.pct_change().dropna()

# === Kennzahlen pro ETF ===
print("Berechne Kennzahlen...")
cagr = prices.apply(annualized_cagr)
vol = rets.std() * np.sqrt(ANN_FACTOR)
sharpe = cagr / vol
cum_returns = (1 + rets).cumprod()

# Max Drawdown
mdd = cum_returns.apply(lambda s: max_drawdown(s))

summary = pd.DataFrame({
    "CAGR": cagr,
    "Volatility": vol,
    "Sharpe": sharpe,
    "MaxDrawdown": mdd
}).round(6)

# Speichern Kennzahlen
summary.to_csv(f"{OUT_DIR}/summary_metrics.csv")
print(f"Kennzahlen gespeichert: {OUT_DIR}/summary_metrics.csv")

# === Kumulative Returns Plot ===
plt.figure(figsize=(10,6))
for col in cum_returns.columns:
    plt.plot(cum_returns.index, cum_returns[col], label=col)
plt.legend()
plt.title("Kumulative Returns (Total Return, reinvested)")
plt.ylabel("Kumulativer Faktor")
plt.xlabel("Datum")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/cumulative_returns.png", dpi=150)
plt.close()
print(f"Kumulative Returns gespeichert: {OUT_DIR}/cumulative_returns.png")

# === Drawdown Plot (Portfolio- und Einzel-ETFs) ===
plt.figure(figsize=(10,6))
for col in cum_returns.columns:
    peak = cum_returns[col].cummax()
    dd = (cum_returns[col] / peak) - 1.0
    plt.plot(dd.index, dd, label=col)
plt.legend()
plt.title("Drawdown (Einzelne ETFs)")
plt.ylabel("Drawdown")
plt.xlabel("Datum")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/drawdown.png", dpi=150)
plt.close()
print(f"Drawdown-Plot gespeichert: {OUT_DIR}/drawdown.png")

# === Korrelationsmatrix (Renditen) ===
corr = rets.corr()
plt.figure(figsize=(8,6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Korrelationsmatrix (tÃƒÂ¤gliche Renditen)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/correlation_heatmap.png", dpi=150)
plt.close()
print(f"Korrelations-Heatmap gespeichert: {OUT_DIR}/correlation_heatmap.png")



# === Einfacher Rebalancing Backtest (gleichgewichtet) ===
print("Starte Rebalancing-Backtest...")
weights = pd.Series(1.0 / len(ETFS), index=ETFS)

# Stelle sicher, dass prices und rets dieselbe Index-Frequenz haben
prices = prices.asfreq('B').ffill()            # Business days, forward-fill missing
rets = prices.pct_change().fillna(0)           # neu berechnete tägliche Renditen, keine NaNs

# Bestimme Rebalancing-Perioden (verwende 'YE' statt 'Y' wegen Deprecation)
period_starts = prices.resample(REBALANCE_FREQ).first().index

# Simpler, korrekter Weg: für jeden Periode-Bereich die täglichen Portfolio-Renditen berechnen
pv = pd.Series(index=prices.index, dtype=float)
current_factor = 1.0

for i in range(len(period_starts)):
    start = period_starts[i]
    end = period_starts[i+1] if i+1 < len(period_starts) else prices.index[-1]
    mask = (prices.index >= start) & (prices.index <= end)
    if not mask.any():
        continue
    # tägliche Renditen für die Periode, ausgerichtet auf prices index
    daily_rets = rets.loc[mask, ETFS].fillna(0)
    # Portfolio tägliche Rendite = gewichtete Summe
    port_daily = daily_rets.dot(weights)
    # kumulative Entwicklung in der Periode, multipliziert mit Startfaktor
    period_cum = (1 + port_daily).cumprod() * current_factor
    pv.loc[mask] = period_cum.values
    # setze neuen Startfaktor für nächste Periode auf letzten Wert dieser Periode
    current_factor = period_cum.iloc[-1]
    # rebalance: weights bleiben gleich (gleichgewichtet), so nichts zu tun

# Fallback: fülle evtl. NaNs
pv = pv.fillna(method="ffill").fillna(1.0)


# Save backtest cumulative
pv.to_csv(f"{OUT_DIR}/backtest_cumulative.csv")
plt.figure(figsize=(10,6))
plt.plot(pv.index, pv.values, label="Equal-weight annual rebalance")
plt.title("Backtest: Gleichgewichtetes Portfolio (jÃƒÂ¤hrliches Rebalancing)")
plt.ylabel("Kumulativer Faktor")
plt.xlabel("Datum")
plt.legend()
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/backtest_cumulative.png", dpi=150)
plt.close()
print(f"Backtest Ergebnisse gespeichert: {OUT_DIR}/backtest_cumulative.png and backtest_cumulative.csv")

# === ErgÃƒÂ¤nzende Kennzahlen fÃƒÂ¼r das Backtest-Portfolio ===
# annualized return
pv_series = pv.dropna()
backtest_cagr = (pv_series.iloc[-1] / pv_series.iloc[0]) ** (ANN_FACTOR / len(pv_series.pct_change().dropna())) - 1
backtest_vol = pv_series.pct_change().std() * np.sqrt(ANN_FACTOR)
backtest_sharpe = backtest_cagr / backtest_vol
backtest_mdd = max_drawdown(pv_series)

backtest_summary = pd.DataFrame({
    "CAGR": [backtest_cagr],
    "Volatility": [backtest_vol],
    "Sharpe": [backtest_sharpe],
    "MaxDrawdown": [backtest_mdd]
}, index=["EqualWeight_AnnualRebalance"]).round(6)

backtest_summary.to_csv(f"{OUT_DIR}/backtest_summary.csv")
print(f"Backtest Kennzahlen gespeichert: {OUT_DIR}/backtest_summary.csv")

print("Fertig.")
