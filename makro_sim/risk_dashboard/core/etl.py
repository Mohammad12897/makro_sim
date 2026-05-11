# risk_dashboard/core/etl.py
import pandas as pd
from typing import Tuple, Dict, List
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.data_loader import fetch_prices

def build_ticker_list(etf_universes: Dict) -> List[str]:
    return [v["ticker"] for v in etf_universes.values() if v.get("ticker")]

def load_prices_for_universe(start: str = "2018-01-01", end: str = None) -> Tuple[pd.DataFrame, List[str], Dict[str,str]]:
    """
    Lädt historische Preise für alle Ticker in ETF_UNIVERSES.
    Rückgabe:
      - prices_df: DataFrame mit Datum als Index und Spalten = config-keys (z. B. 'global_equity_etf')
      - missing_total: Liste der config-keys, die keine Daten lieferten
      - mapping: success_ticker -> config_key (z. B. 'VWRL.L' -> 'global_equity_etf')
    """
    tickers = build_ticker_list(ETF_UNIVERSES)
    if not tickers:
        return pd.DataFrame(), [], {}

    # fetch_prices liefert keys = exakter ticker oder success_ticker mit suffix
    prices_dict = fetch_prices(tickers, start=start, end=end)
    if not prices_dict:
        return pd.DataFrame(), list(ETF_UNIVERSES.keys()), {}

    # --- Mapping: success_ticker -> config_key ---
    success_to_key: Dict[str, str] = {}
    matched_keys = set()

    for cfg_key, meta in ETF_UNIVERSES.items():
        base = meta.get("ticker")
        if not base:
            continue
        # exact match first
        if base in prices_dict and not prices_dict[base].empty:
            success_to_key[base] = cfg_key
            matched_keys.add(cfg_key)
            continue
        # heuristic: find any success key that startswith base and has data
        for success in prices_dict.keys():
            if success.startswith(base) and not prices_dict[success].empty:
                success_to_key[success] = cfg_key
                matched_keys.add(cfg_key)
                break

    # --- Build DataFrame from prices_dict and rename mapped columns to config keys ---
    try:
        prices_df = pd.concat(prices_dict.values(), axis=1)
    except ValueError:
        return pd.DataFrame(), list(ETF_UNIVERSES.keys()), {}

    prices_df.columns = list(prices_dict.keys())

    # rename only the success_tickers we mapped
    if success_to_key:
        prices_df = prices_df.rename(columns=success_to_key)

    # normalize index and sort
    prices_df.index = pd.to_datetime(prices_df.index, errors="coerce")
    prices_df = prices_df.sort_index()

    # --- missing_total: config keys not present or ohne Daten ---
    missing_total: List[str] = []
    for cfg_key, meta in ETF_UNIVERSES.items():
        if cfg_key in prices_df.columns and not prices_df[cfg_key].dropna().empty:
            continue
        missing_total.append(cfg_key)

    # mapping zurückgeben: success_ticker -> config_key (für Debug/UI)
    return prices_df, missing_total, success_to_key
