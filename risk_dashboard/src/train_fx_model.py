from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib

def create_features(df):
    df = df.copy()
    df["return"] = df["Close"].pct_change()
    df["lag1"] = df["Close"].shift(1)
    df["lag2"] = df["Close"].shift(2)
    df["lag3"] = df["Close"].shift(3)
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["volatility"] = df["return"].rolling(10).std()
    df = df.dropna()
    return df

def train_fx_model():
    base_path = Path(__file__).resolve().parents[1]
    df = pd.read_csv(base_path / "data" / "fx_data_usd_eur.csv")

    df = create_features(df)

    X = df[["lag1", "lag2", "lag3", "ma5", "ma20", "volatility"]]
    y = df["Close"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42
    )
    model.fit(X_train, y_train)

    model_path = base_path / "models"
    model_path.mkdir(exist_ok=True)
    out_file = model_path / "rf_model_usd_eur.joblib"
    joblib.dump(model, out_file)

    print(f"FX model saved to: {out_file}")

if __name__ == "__main__":
    train_fx_model()