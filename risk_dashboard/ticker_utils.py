# risk_dashboard/ticker_utils.py
from typing import List, Sequence

# --- utility: normalize ticker (simple example, adapt to your normalize_ticker) ---
def normalize_ticker_simple(t: str) -> str:
    if not t:
        return ""
    t = str(t).strip().upper()
    return t

def normalize_ticker(t: str) -> str:
    t = str(t).strip()
    if not t:
        return ""
    t = t.replace(":", ".").lstrip("$")
    # crypto mapping example
    if t.upper() in ("BTC", "BTCUSD"):
        return "BTC-USD"
    return t.upper()

def _normalize_tickers(tickers: Sequence[str]) -> List[str]:
    out = []
    for t in tickers:
        if not t:
            continue
        s = str(t).strip().upper()
        s = s.replace(" ", "").replace("/", "")
        out.append(s)
    return out

def normalize_weights_keys(weights: dict, price_cols: list) -> dict:
    norm = {}
    price_set = {str(c).strip().upper() for c in price_cols}
    for k, v in (weights or {}).items():
        nk = normalize_ticker(str(k)).upper()
        if nk in price_set:
            norm[nk] = float(v)
        else:
            # try other variants
            if str(k).upper() in price_set:
                norm[str(k).upper()] = float(v)
    return norm
