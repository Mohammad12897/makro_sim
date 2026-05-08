# risk_dashboard/src/core/fred_loader.py
import pandas as pd
import requests

def load_fred_series_api(series_id: str, api_key: str) -> pd.DataFrame:
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
    )
    r = requests.get(url).json()
    obs = r["observations"]

    df = pd.DataFrame(obs)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "value"]]