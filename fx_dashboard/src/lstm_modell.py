#Abschnitt 6 — LSTM‑Modell (Deep Learning)
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

scaler = MinMaxScaler()
scaled = scaler.fit_transform(df[[target]])

sequence_length = 30

X_lstm = []
y_lstm = []

for i in range(len(scaled) - sequence_length):
    X_lstm.append(scaled[i:i+sequence_length])
    y_lstm.append(scaled[i+sequence_length])

X_lstm = np.array(X_lstm)
y_lstm = np.array(y_lstm)

split = int(len(X_lstm) * 0.8)
X_train_lstm, X_test_lstm = X_lstm[:split], X_lstm[split:]
y_train_lstm, y_test_lstm = y_lstm[:split], y_lstm[split:]

model_lstm = Sequential([
    LSTM(64, return_sequences=False, input_shape=(sequence_length, 1)),
    Dense(1)
])

model_lstm.compile(optimizer="adam", loss="mse")
model_lstm.fit(X_train_lstm, y_train_lstm, epochs=10, batch_size=16)
