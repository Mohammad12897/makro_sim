#src/data_loader.py
<<<<<<< HEAD
import pandas as pd

def load_macro_data(path: str = "data/synthetic_macro.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    return df
=======
from pathlib import Path
import pandas as pd

def load_macro_data(
    path: str = str(Path(__file__).resolve().parents[1] / "data" / "synthetic_macro.csv")
) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    return df
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
