from pathlib import Path
import numpy as np
import pandas as pd

def generate_fx_data(n_days=365):
    base_path = Path(__file__).resolve().parents[1]
    data_path = base_path / "data"
    data_path.mkdir(exist_ok=True)

    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="D")

    np.random.seed(42)
    close = 1.05 + np.cumsum(np.random.normal(0, 0.002, n_days))

    df = pd.DataFrame({"date": dates, "Close": close})
    df.to_csv(data_path / "fx_data_usd_eur.csv", index=False)

    print("FX data generated:", data_path / "fx_data_usd_eur.csv")

if __name__ == "__main__":
    generate_fx_data()