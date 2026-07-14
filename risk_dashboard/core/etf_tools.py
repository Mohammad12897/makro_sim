# risk_dashboard/core/etf_tools.py
import logging
from typing import List, Dict, Any, Tuple
import pandas as pd
import yfinance as yf
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Placeholder ETF_CANDIDATES import (user can fill risk_dashboard/config/etf_candidates.py)
try:
    from risk_dashboard.config.etf_candidates import ETF_CANDIDATES
except Exception:
    ETF_CANDIDATES = {}

def get_etf_candidates_for_index(index_name: str) -> pd.DataFrame:
    """Return candidates DataFrame with standardized columns."""
    items = ETF_CANDIDATES.get(index_name, [])
    df = pd.DataFrame(items)
    for col in ("ticker", "name", "domicile", "expense_ratio", "aum", "replication"):
        if col not in df.columns:
            df[col] = None
    return df

# -------------------------
# Scoring helpers
# -------------------------
def score_ter(ter: float) -> float:
    """Score TER: returns 0..1 (1 best). ter expected as decimal (e.g., 0.001 = 0.1%)."""
    if ter is None or np.isnan(ter):
        return 0.4
    if ter < 0.0005:
        return 1.0
    if ter < 0.001:
        return 0.85
    if ter < 0.002:
        return 0.6
    if ter < 0.004:
        return 0.3
    return 0.0

def score_aum(aum: float) -> float:
    """Score AUM: 0..1 (1 best)."""
    if aum is None or np.isnan(aum):
        return 0.3
    if aum >= 1_000_000_000:
        return 1.0
    if aum >= 500_000_000:
        return 0.8
    if aum >= 100_000_000:
        return 0.6
    if aum >= 10_000_000:
        return 0.4
    return 0.0

def score_replication(replication: str) -> float:
    """Score replication: physical preferred."""
    if not replication:
        return 0.5
    rep = str(replication).lower()
    if "physical" in rep:
        return 1.0
    if "synthetic" in rep:
        return 0.2
    return 0.6

def score_liquidity(spread_pct: float = None, avg_volume: float = None) -> float:
    """Score liquidity using spread (preferred low) or volume (preferred high)."""
    if spread_pct is not None and not np.isnan(spread_pct):
        if spread_pct < 0.01:
            return 1.0
        if spread_pct < 0.05:
            return 0.8
        if spread_pct < 0.1:
            return 0.5
        return 0.0
    if avg_volume is not None and not np.isnan(avg_volume):
        if avg_volume > 1_000_000:
            return 1.0
        if avg_volume > 200_000:
            return 0.8
        if avg_volume > 50_000:
            return 0.5
        return 0.2
    return 0.4

def score_tracking_error(tracking_error_pct: float) -> float:
    """Lower tracking error is better. Input as percent (e.g., 0.5 for 0.5%)."""
    if tracking_error_pct is None or np.isnan(tracking_error_pct):
        return 0.5
    if tracking_error_pct < 0.1:
        return 1.0
    if tracking_error_pct < 0.3:
        return 0.8
    if tracking_error_pct < 0.6:
        return 0.5
    return 0.0

# -------------------------
# Presets
# -------------------------
PRESETS = {
    "Balanced": {"ter":0.25, "aum":0.20, "tracking":0.25, "replication":0.10, "liquidity":0.20},
    "Conservative": {"ter":0.15, "aum":0.25, "tracking":0.35, "replication":0.10, "liquidity":0.15},
    "Aggressive": {"ter":0.35, "aum":0.15, "tracking":0.20, "replication":0.10, "liquidity":0.20},
}

def get_preset_weights(name: str) -> Dict[str, float]:
    return PRESETS.get(name, PRESETS["Balanced"])

# -------------------------
# Main scoring function
# -------------------------
def compute_etf_score_components(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute component scores (0..1) and weighted total (0..1).
    Expects row to contain keys: expense_ratio (decimal), aum (float), replication (str),
    tracking_error (percent), spread_pct (percent), avg_volume (float).
    """
    ter = None
    try:
        ter = float(row.get("expense_ratio")) if row.get("expense_ratio") is not None else None
    except Exception:
        ter = None
    aum = None
    try:
        aum = float(row.get("aum")) if row.get("aum") is not None else None
    except Exception:
        aum = None
    replication = row.get("replication")
    tracking_error = None
    try:
        tracking_error = float(row.get("tracking_error")) if row.get("tracking_error") is not None else None
    except Exception:
        tracking_error = None
    spread = None
    try:
        spread = float(row.get("spread_pct")) if row.get("spread_pct") is not None else None
    except Exception:
        spread = None
    avg_vol = None
    try:
        avg_vol = float(row.get("avg_volume")) if row.get("avg_volume") is not None else None
    except Exception:
        avg_vol = None

    s_ter = score_ter(ter)
    s_aum = score_aum(aum)
    s_tracking = score_tracking_error(tracking_error)
    s_rep = score_replication(replication)
    s_liq = score_liquidity(spread, avg_vol)

    # default weights (balanced)
    weights = get_preset_weights("Balanced")
    total = (weights["ter"] * s_ter +
             weights["aum"] * s_aum +
             weights["tracking"] * s_tracking +
             weights["replication"] * s_rep +
             weights["liquidity"] * s_liq)
    # scale to 0..100 for readability
    return {
        "ter_score": round(s_ter, 4),
        "aum_score": round(s_aum, 4),
        "tracking_score": round(s_tracking, 4),
        "replication_score": round(s_rep, 4),
        "liquidity_score": round(s_liq, 4),
        "total_score": round(total * 100, 2)
    }

# -------------------------
# Price download (unchanged, minimal cache)
# -------------------------
_price_cache = {}

def download_prices(tickers: List[str], start: str = "2018-01-01", end: str = None) -> pd.DataFrame:
    """Download Close prices for tickers using yfinance. Returns DataFrame indexed by Date with tickers as columns."""
    end = end or datetime.today().strftime("%Y-%m-%d")
    key = (tuple(sorted(tickers)), start, end)
    if key in _price_cache:
        return _price_cache[key]
    try:
        df = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=False)
    except Exception as e:
        logger.exception("yfinance download failed: %s", e)
        return pd.DataFrame()
    # Extract Close prices robustly
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            close = df["Close"].copy()
        else:
            lvl0 = df.columns.get_level_values(0)
            close_cols = [c for c in lvl0 if str(c).lower().startswith("close")]
            if close_cols:
                close = df[close_cols[0]]
            else:
                close = df.iloc[:, :]
    else:
        close = df.copy()
    close.columns = [str(c).strip() for c in close.columns]
    _price_cache[key] = close
    return close
