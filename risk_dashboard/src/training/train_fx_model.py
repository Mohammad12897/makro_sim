#  risk_dashboard/src/training/train_fx_model.py
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib

from risk_dashboard.src.core.utils import get_data_path, get_models_path
from risk_dashboard.src.features.fx_features import create_fx_features

def train_fx_model():
    data_path = get_data_path()
    models_path = get_models_path()

    df = pd.read_csv(data_path / "fx_data_usd_eur.csv")
    df_feat = create_fx_features(df)

    X = df_feat[["lag1", "lag2", "lag3", "ma5", "ma20", "volatility"]]
    y = df_feat["Close"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42
    )
    model.fit(X_train, y_train)

    models_path.mkdir(exist_ok=True)
    out_file = models_path / "rf_model_usd_eur.joblib"
    joblib.dump(model, out_file)
    print(f"FX model saved to: {out_file}")

if __name__ == "__main__":
    train_fx_model()