#risk_dashboard/core/macro_loader.py
import os
import time
from pathlib import Path
import pandas as pd
import requests
from risk_dashboard.core.config_loader import load_config
from pandas_datareader import data as web
from risk_dashboard.core.market_engine import download_etf_history, build_market_risk_factors



config = load_config()
FRED_API_KEY = config["fred"]["api_key"]
CACHE_DIR = Path(config["fred"].get("cache_dir", "cache"))
MAX_AGE_DAYS = config["fred"].get("max_age_days", 3)

CACHE_DIR.mkdir(exist_ok=True)

def _cache_path(series_id: str) -> Path:
    return CACHE_DIR / f"{series_id}.csv"

def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds < MAX_AGE_DAYS * 24 * 3600

def _fetch_from_fred(series_id: str) -> pd.DataFrame:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json"
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["observations"]
    df = pd.DataFrame(data)
    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def load_macro_series(series_id: str) -> pd.DataFrame:
    """
    Lädt eine einzelne Makroserie von FRED.
    Gibt DataFrame mit Spalten: date, value
    """
    df = web.DataReader(series_id, "fred")
    df = df.rename(columns={series_id: "value"})
    df.index.name = "date"
    df = df.reset_index()
    return df


def load_macro_data() -> pd.DataFrame:
    """
    Lädt alle Makroserien für Szenario-Engine.
    """
    df = pd.DataFrame()

    df["gdp"] = web.DataReader("GDP", "fred")
    df["cpi"] = web.DataReader("CPIAUCSL", "fred")
    df["unrate"] = web.DataReader("UNRATE", "fred")
    df["fedfunds"] = web.DataReader("FEDFUNDS", "fred")

    df = df.dropna()
    df.index.name = "date"
    return df


def load_market_data():
    prices = download_etf_history(["SPY"], period="10y")
    return build_market_risk_factors(prices)
