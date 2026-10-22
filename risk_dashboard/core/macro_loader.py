#risk_dashboard/core/macro_loader.py
import os
import time
from pathlib import Path
from typing import Optional
import pandas as pd
import requests
import csv
from io import StringIO
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


def load_macro_series_old(series_id: str) -> pd.DataFrame:
    """
    Lädt eine einzelne Makroserie von FRED.
    Gibt DataFrame mit Spalten: date, value
    """
    df = web.DataReader(series_id, "fred")
    df = df.rename(columns={series_id: "value"})
    df.index.name = "date"
    df = df.reset_index()
    return df



import logging
import requests
import pandas as pd
import csv
import time
from io import StringIO
from pandas_datareader import data as web
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _requests_session_with_retries(total=3, backoff_factor=0.5, status_forcelist=(429,500,502,503,504)):
    s = requests.Session()
    retries = Retry(total=total, backoff_factor=backoff_factor, status_forcelist=list(status_forcelist),
                    allowed_methods=frozenset(["GET", "POST"]))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def _safe_write_debug(text: str, series_id: str):
    debug_dir = Path.home() / ".makro_sim_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    fname = debug_dir / f"fred_{series_id}_response_{int(time.time())}.txt"
    try:
        fname.write_text(text, encoding="utf-8", errors="replace")
    except Exception:
        logger.exception("Failed to write debug response to %s", fname)

def _safe_write_cache(df: pd.DataFrame, series_id: str):
    cache_dir = Path.home() / ".makro_sim_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(cache_dir / f"{series_id}.csv", index=True)
    except Exception:
        logger.exception("Failed to write cache for %s", series_id)

def _read_cache(series_id: str) -> pd.DataFrame | None:
    cache_file = Path.home() / ".makro_sim_cache" / f"{series_id}.csv"
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True, engine="python", encoding="utf-8-sig")
            if df.shape[1] >= 1:
                if df.columns[0] != "value":
                    df = df.rename(columns={df.columns[0]: "value"})
                df.index.name = "date"
                return df.reset_index()
        except Exception:
            logger.exception("Failed to read cache for %s", series_id)
    return None

def load_macro_series(series_id: str, max_retries: int = 3, backoff: float = 1.0) -> pd.DataFrame:
    """
    Robuster Loader für FRED Serien.
    Liefert DataFrame mit Spalten: date, value.
    Bei Fehlern: leeres DataFrame statt Exception.
    """
    # 0) Try local cache first
    try:
        cached = _read_cache(series_id)
        if cached is not None:
            logger.debug("Loaded %s from local cache", series_id)
            return cached
    except Exception:
        logger.exception("Cache read failed for %s", series_id)

    # 1) Try pandas_datareader
    try:
        df = web.DataReader(series_id, "fred")
        df = df.rename(columns={series_id: "value"})
        df.index.name = "date"
        _safe_write_cache(df, series_id)
        return df.reset_index()
    except Exception as e:
        logger.exception("DataReader failed, will try manual fetch: %s", e)

    # 2) Manual fetch with retries and robust parsing
    url = f"https://fred.stlouisfed.org/series/{series_id}/downloaddata/{series_id}.csv"
    session = _requests_session_with_retries(total=max_retries, backoff_factor=0.5)

    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(url, timeout=20, headers={"User-Agent": "makro_sim/1.0"})
            text = r.text or ""
            logger.debug("Manual fetch attempt=%d status=%s len=%d url=%s", attempt, r.status_code, len(text), url)

            # If response is HTML or not 200, save debug and break/continue
            if r.status_code != 200 or "<html" in text.lower():
                _safe_write_debug(text, series_id)
                logger.error("Unexpected response from FRED (not CSV). status=%s", r.status_code)
                if "<html" in text.lower():
                    break
            else:
                sample = "\n".join(text.splitlines()[:20])
                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample)
                    delim = dialect.delimiter
                except Exception:
                    delim = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","

                df = pd.read_csv(
                    StringIO(text),
                    index_col=0,
                    parse_dates=True,
                    engine="python",
                    sep=delim,
                    on_bad_lines="warn",
                    encoding="utf-8-sig"
                )

                if series_id in df.columns:
                    df = df.rename(columns={series_id: "value"})
                else:
                    if len(df.columns) >= 1:
                        df = df.rename(columns={df.columns[0]: "value"})
                df.index.name = "date"
                _safe_write_cache(df, series_id)
                return df.reset_index()
        except Exception:
            logger.exception("Manual fetch/parse attempt %d failed for %s", attempt, series_id)

        time.sleep(backoff * (2 ** (attempt - 1)))

    logger.warning("Returning empty DataFrame for %s after failed attempts", series_id)
    return pd.DataFrame(columns=["date", "value"])

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

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
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
