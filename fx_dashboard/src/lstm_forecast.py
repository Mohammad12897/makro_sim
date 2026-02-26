#Abschnitt 7 — LSTM‑Forecast (30 Tage)
last_seq = scaled[-sequence_length:]

future_lstm = []

current_seq = last_seq.copy()

for i in range(30):
    pred = model_lstm.predict(current_seq.reshape(1, sequence_length, 1))[0][0]
    future_lstm.append(pred)

    current_seq = np.vstack([current_seq[1:], [[pred]]])

future_lstm = scaler.inverse_transform(np.array(future_lstm).reshape(-1,1))
future_lstm[:10]
