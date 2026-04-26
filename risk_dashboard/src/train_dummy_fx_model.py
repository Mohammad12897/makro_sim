from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

def train_dummy_fx_model():
    # Basis-Pfad: risk_dashboard/
    base_path = Path(__file__).resolve().parents[1]

    # Daten laden
    df = pd.read_csv(base_path / "data" / "fx_data_usd_eur.csv")

    # Feature: letzter Close-Wert
    X = df[["Close"]].values
    y = df["Close"].shift(-1).fillna(method="ffill").values  # nächster Tag als Ziel

    # Einfaches Dummy-Modell
    model = RandomForestRegressor(
        n_estimators=10,
        random_state=42
    )
    model.fit(X, y)

    # Modell speichern
    model_path = base_path / "models"
    model_path.mkdir(exist_ok=True)
    out_file = model_path / "rf_model_usd_eur.joblib"
    joblib.dump(model, out_file)

    print(f"Dummy FX model saved to: {out_file}")

if __name__ == "__main__":
    train_dummy_fx_model()