import pandas as pd
import joblib

def load_data(path):
    df = pd.read_csv(path)
    return df

def load_scaler(path):
    return joblib.load(path)
