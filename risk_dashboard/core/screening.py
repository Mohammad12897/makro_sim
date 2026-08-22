import pandas as pd
from typing import Tuple, Dict, List, Any
from risk_dashboard.ui.helpers import passes_liquidity, normalize_ticker

def momentum(series: pd.Series) -> float:
    # robust: berechne Renditen nur, wenn genügend Werte vorhanden und handle NaNs
    s = series.dropna()
    if s.empty:
        return 0.0
    def pct(n):
        if len(s) > n:
            val = s.pct_change(n).iloc[-1]
            return float(val) if pd.notna(val) else 0.0
        return 0.0
    return 0.3 * pct(63) + 0.3 * pct(126) + 0.4 * pct(252)

def quality(ticker_meta: Dict[str, Any]) -> float:
    mc = ticker_meta.get("market_cap") or 0
    try:
        mc = float(mc)
    except Exception:
        mc = 0.0
    return mc / (1e9 + mc) if mc >= 0 else 0.0

def value_score(ticker_meta: Dict[str, Any]) -> float:
    pe = ticker_meta.get("pe_ratio")
    try:
        pe = float(pe)
        return 1.0 / pe if pe > 0 else 0.0
    except Exception:
        return 0.0

def screen_and_rank(
    universe_meta: pd.DataFrame,
    price_history: Dict[str, pd.Series],
    top_n: int = 20
) -> Tuple[List[str], Dict[str, float]]:
    """
    universe_meta: DataFrame mit mindestens Spalte 'ticker' und optionalen Metadaten
    price_history: dict[ticker] -> pd.Series (Adj Close)
    returns: (selected_tickers, scores_dict)
    """
    scores: Dict[str, float] = {}

    # Wenn universe_meta ein dict ist, konvertiere zu DataFrame-ähnlicher Iteration
    if isinstance(universe_meta, dict):
        items = universe_meta.items()
    else:
        items = universe_meta.iterrows()

    for _, meta in items:
        # meta kann Series (DataFrame row) oder dict sein
        if isinstance(meta, pd.Series):
            meta_dict = meta.to_dict()
        else:
            meta_dict = dict(meta)

        t = meta_dict.get("ticker")
        if not t:
            continue
        t = normalize_ticker(t)

        if not passes_liquidity(meta_dict):
            continue

        series = price_history.get(t)
        if series is None or len(series.dropna()) < 60:
            continue

        m = momentum(series)
        q = quality(meta_dict)
        v = value_score(meta_dict)
        scores[t] = 0.4 * m + 0.3 * q + 0.3 * v

    # sortiere nach Score und gib Top N zurück
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    selected = [t for t, _ in ranked[:top_n]]
    return selected, scores
