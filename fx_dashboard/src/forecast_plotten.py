#Abschnitt 5 — Forecast plotten
import matplotlib.pyplot as plt

plt.figure(figsize=(12,5))
plt.plot(df.index[-200:], df["usd_eur"].tail(200), label="Real")
plt.plot(pd.date_range(df.index[-1], periods=30, freq="D"), future, label="Forecast")
plt.legend()
plt.title("USD/EUR – 30‑Day Forecast")
plt.show()
