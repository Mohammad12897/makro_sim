import pandas as pd
from risk_dashboard.core.helpers import passes_liquidity

def momentum(series: pd.Series) -> float:
    r3 = series.pct_change(63).iloc[-1] if len(series) > 63 else 0.0
    r6 = series.pct_change(126).iloc[-1] if len(series) > 126 else 0.0
    r12 = series.pct_change(252).iloc[-1] if len(series) > 252 else 0.0
    return 0.3 * r3 + 0.3 * r6 + 0.4 * r12

def quality(ticker_meta: dict) -> float:
    # placeholder: use market_cap as proxy
    mc = ticker_meta.get("market_cap") or 0
    return float(mc) / (1e9 + mc)

def value_score(ticker_meta: dict) -> float:
    # placeholder: if P/E available, invert it; else 0
    pe = ticker_meta.get("pe_ratio")
    return 1.0 / pe if pe and pe > 0 else 0.0

def screen_and_rank(universe_meta: pd.DataFrame, price_history: dict, top_n: int = 20):
    scores = {}
    for _, meta in universe_meta.iterrows():
        t = meta["ticker"]
        if not passes_liquidity(meta):
            continue
        series = price_history.get(t)
        if series is None or len(series) < 60:
            continue
        m = momentum(series)
        q = quality(meta)
        v = value_score(meta)
        scores[t] = 0.4 * m + 0.3 * q + 0.3 * v
    selected = sorted(scores, key=scores.get, reverse=True)[:top_n]
    return selected, scores
