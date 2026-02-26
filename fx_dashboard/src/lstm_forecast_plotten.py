#Abschnitt 8 — LSTM‑Forecast plotten
plt.figure(figsize=(12,5))
plt.plot(df.index[-200:], df[target].tail(200), label="Real")
plt.plot(pd.date_range(df.index[-1], periods=30, freq="D"), future_lstm, label="LSTM Forecast")
plt.legend()
plt.title("USD/EUR – LSTM 30‑Day Forecast")
plt.show()
