# scripts/filter_tickers.py
# python scripts/filter_tickers.py
from typing import List
from scripts.ticker_cache import validate_ticker_with_cache

def filter_valid_tickers(tickers: List[str]) -> List[str]:
    valid = []
    for t in tickers:
        t_norm = (t or "").strip().upper()
        if not t_norm:
            continue
        if validate_ticker_with_cache(t_norm):
            valid.append(t_norm)
    return list(dict.fromkeys(valid))

if __name__ == "__main__":
    tickers = ["XDAX.DE","XUDE.DE","EUNL.DE","VWCE.DE","SPY"]
    valid = filter_valid_tickers(tickers)
    print("Valid:", valid)
