# This script generates synthetic macroeconomic data for demonstration purposes.
# src/generate_synthetic_macro.py
from pathlib import Path
import numpy as np
import pandas as pd

def generate_synthetic_fx(n_days: int = 365):
    base_path = Path(__file__).resolve().parents[1]
    data_path = base_path / "data"
    data_path.mkdir(exist_ok=True)

    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="D")

    np.random.seed(42)

    # Realistische FX-Simulation (Random Walk)
    close = 1.05 + np.cumsum(np.random.normal(0, 0.002, n_days))

    df = pd.DataFrame({
        "date": dates,
        "Close": close
    })

    out_path = data_path / "fx_data_usd_eur.csv"
    df.to_csv(out_path, index=False)

    print(f"Synthetic FX data saved to: {out_path}")

if __name__ == "__main__":
    generate_synthetic_fx()