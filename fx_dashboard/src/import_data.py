import joblib

# Random Forest speichern
joblib.dump(model, "rf_model_usd_eur.joblib")

# Skaler und LSTM speichern
joblib.dump(scaler, "scaler_usd_eur.joblib")
model_lstm.save("lstm_usd_eur.keras")

# Letzte Daten für Dashboard speichern
df.to_csv("fx_data_usd_eur.csv")
print("Modelle und Daten gespeichert.")
