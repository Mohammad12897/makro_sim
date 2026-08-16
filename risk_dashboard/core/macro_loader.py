#risk_dashboard/core/macro_loader.py
import os
import time
from pathlib import Path
from typing import Optional
import pandas as pd
import requests
from risk_dashboard.core.config_loader import load_config
from pandas_datareader import data as web
from risk_dashboard.core.market_engine import download_etf_history, build_market_risk_factors
import logging

logger = logging.getLogger(__name__)

config = load_config()


REQUIRED_MACRO_COLS = ["yield_curve", "inflation", "growth"]

# Robustes Lesen des FRED API Keys: zuerst config.yaml, sonst Umgebungsvariable
FRED_API_KEY = config.get("fred", {}).get("api_key") or os.environ.get("FRED_API_KEY")
if not FRED_API_KEY:
    raise RuntimeError("FRED API key not configured. Set risk_dashboard/config.yaml or FRED_API_KEY env var.")

CACHE_DIR = Path(config.get("fred", {}).get("cache_dir", "cache"))
MAX_AGE_DAYS = config.get("fred", {}).get("max_age_days", 3)

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
    try:
        df = pd.DataFrame()
        df["gdp"] = web.DataReader("GDP", "fred")
        df["cpi"] = web.DataReader("CPIAUCSL", "fred")
        df["unrate"] = web.DataReader("UNRATE", "fred")
        df["fedfunds"] = web.DataReader("FEDFUNDS", "fred")
        df = df.dropna()
        df.index.name = "date"
        return df
    except Exception:
        # Fallback für Offline/Dev
        return pd.DataFrame({
            "inflation": [2.1, 2.4, 3.0, 3.4],
            "yield_curve": [0.5, 0.2, -0.1, -0.3],
            "growth": [1.5, 1.2, 0.4, -0.2]
        })

def load_and_validate_macro_data() -> Optional[pd.DataFrame]:
    """
    Lädt Makrodaten (via load_macro_data), wendet sinnvolle Fallbacks an
    und validiert erforderliche Spalten. Gibt None zurück bei Fehlern.
    """
    try:
        df = load_macro_data()  # zentrale Implementierung im selben Modul
    except Exception:
        logger.exception("Fehler beim Laden der Makrodaten")
        return None

    if df is None or df.empty:
        logger.error("load_macro_data returned empty DataFrame")
        return None

    # --- yield_curve Fallback (nur wenn yield_curve fehlt) ---
    if "yield_curve" not in df.columns:
        logger.warning("yield_curve fehlt — Fallback wird angewendet")
        if "10y" in df.columns and "2y" in df.columns:
            df["yield_curve"] = df["10y"] - df["2y"]
        elif "fedfunds" in df.columns:
            df["yield_curve"] = df["fedfunds"].diff().fillna(0)
        else:
            df["yield_curve"] = 0.0
        logger.info("yield_curve Fallback angewendet")

    # nach yield_curve-Fallback ergänzen
    if "inflation" not in df.columns:
        logger.warning("inflation fehlt — versuche Fallback aus CPI oder Proxy")
        if "cpi" in df.columns:
            # Beispiel: jährliche Veränderung der CPI als Inflation proxy
            df["inflation"] = df["cpi"].pct_change(12).mul(100).bfill().fillna(0.0)
        else:
            df["inflation"] = 0.0

    if "growth" not in df.columns:
        logger.warning("growth fehlt — versuche Fallback aus GDP")
        if "gdp" in df.columns:
            df["growth"] = df["gdp"].pct_change(4).mul(100).bfill().fillna(0.0)
            # optional: .fillna(0.0) wenn du keine NaNs erlauben willst
        else:
            df["growth"] = 0.0

    # --- Ende Fallback ---

    # abschließende Validierung
    missing = [c for c in REQUIRED_MACRO_COLS if c not in df.columns]
    if missing:
        logger.warning("Makrodaten unvollständig. Fehlende Spalten: %s", missing)
        return None

    # Optional: setze Indexname, Datentypen o.ä., falls nötig
    if df.index.name is None:
        df.index.name = "date"

    return df


def load_market_data():
    prices = download_etf_history(["SPY"], period="10y")
    return build_market_risk_factors(prices)
