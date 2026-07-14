# risk_dashboard/core/etl.py
import pandas as pd
from typing import Tuple, Dict, List
from risk_dashboard.data.etf_universes import ETF_UNIVERSES
from risk_dashboard.core.data_loader import load_raw_prices_for_universe

def build_ticker_list(etf_universes: Dict) -> List[str]:
    return [v["ticker"] for v in etf_universes.values() if v.get("ticker")]

def load_etf_universe_prices(start: str = "2018-01-01", end: str = None) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """
    Lädt historische Preise für alle Ticker in ETF_UNIVERSES.
    Rückgabe:
      - prices_df: DataFrame mit Datum als Index und Spalten = config-keys
      - missing_total: Liste der config-keys, die keine Daten lieferten
      - mapping: success_ticker -> config_key
    """

    # 1) Universe bauen
    tickers = build_ticker_list(ETF_UNIVERSES)
    if not tickers:
        return pd.DataFrame(), [], {}

    # 2) NEU: robustes Laden aller Ticker
    prices_multi, skipped = load_raw_prices_for_universe(tickers)

    if prices_multi.empty:
        return pd.DataFrame(), list(ETF_UNIVERSES.keys()), {}

    # 3) success_ticker -> config_key Mapping
    success_to_key: Dict[str, str] = {}

    for cfg_key, meta in ETF_UNIVERSES.items():
        base = meta.get("ticker")
        if not base:
            continue

        # Prüfen, ob base oder ein success_ticker geladen wurde
        for loaded in set(prices_multi.index.get_level_values("__ticker")):
            if loaded == base or loaded.startswith(base):
                success_to_key[loaded] = cfg_key
                break

    # 4) DataFrame pivoten: MultiIndex → Wide Format
    prices_df = prices_multi.reset_index().pivot(index="Date", columns="__ticker", values="Close")

    # 5) Spalten umbenennen (success_ticker → config_key)
    prices_df = prices_df.rename(columns=success_to_key)

    # 6) Fehlende config_keys bestimmen
    missing_total = []
    for cfg_key in ETF_UNIVERSES.keys():
        if cfg_key not in prices_df.columns or prices_df[cfg_key].dropna().empty:
            missing_total.append(cfg_key)

    return prices_df, missing_total, success_to_key
