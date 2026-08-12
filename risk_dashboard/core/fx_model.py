# risk_dashboard/src/core/fx_model.py
import pandas as pd
import joblib
from .utils import get_data_path, get_models_path
from risk_dashboard.src.features.fx_features import create_fx_features
import streamlit as st

@st.cache_resource
def load_fx_model():
    models_path = get_models_path()
    model_file = models_path / "rf_model_usd_eur.joblib"
    return joblib.load(model_file)

def get_fx_forecast() -> float:
    data_path = get_data_path()
    df = pd.read_csv(data_path / "fx_data_usd_eur.csv")
    df_feat = create_fx_features(df)
    last_row = df_feat.iloc[-1]
    X = last_row[["lag1", "lag2", "lag3", "ma5", "ma20", "volatility"]].values.reshape(1, -1)
    model = load_fx_model()
    pred = model.predict(X)[0]
    return float(pred)