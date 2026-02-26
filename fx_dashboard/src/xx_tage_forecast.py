#Abschnitt 4 — 30‑Tage‑Forecast (klassisch)
future = []

last_row = df.iloc[-1].copy()

for i in range(30):
    X_future = last_row[features].values.reshape(1, -1)
    pred = model.predict(X_future)[0]

    new_row = last_row.copy()
    new_row["usd_eur"] = pred

    future.append(pred)
    last_row = new_row

future_df = pd.DataFrame({
    "forecast": future
})

future_df
