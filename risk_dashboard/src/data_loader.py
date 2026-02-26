#src/data_loader.py
import pandas as pd

def load_macro_data(path: str = "data/synthetic_macro.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    return df
