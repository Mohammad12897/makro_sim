import joblib
import tensorflow as tf

def load_rf_model(path):
    return joblib.load(path)

def load_lstm_model(path):
    return tf.keras.models.load_model(path)

def predict(model, X):
    return model.predict(X)
