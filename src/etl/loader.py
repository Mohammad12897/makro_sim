# src/etl/loader.py
import pandas as pd
from pathlib import Path
from ..config import DATA_DIR

def discover_local_indicators(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    files = list(data_dir.glob("*"))
    indicators = {}
    for f in files:
        if f.suffix.lower() in [".parquet", ".pq"]:
            try:
                df = pd.read_parquet(f)
                indicators[f.stem] = df
            except Exception:
                continue
        elif f.suffix.lower() in [".csv", ".txt"]:
            try:
                df = pd.read_csv(f)
                indicators[f.stem] = df
            except Exception:
                continue
    return indicators

def load_indicator(name, data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    p_parquet = data_dir / f"{name}.parquet"
    p_csv = data_dir / f"{name}.csv"
    if p_parquet.exists():
        return pd.read_parquet(p_parquet)
    if p_csv.exists():
        return pd.read_csv(p_csv)
    raise FileNotFoundError(name)
