import re

def normalize_ticker(t: str) -> str:
    return t.strip().upper()

def detect_type(ticker: str, etf_df=None, stock_df=None) -> str:
    # Prefer explicit lookup in universes if provided
    if etf_df is not None and ticker in etf_df["ticker"].values:
        return "etf"
    if stock_df is not None and ticker in stock_df["ticker"].values:
        return "stock"
    # fallback heuristic
    if re.search(r"\.L|\.DE|\.MI|\.HK|\.TO", ticker, re.IGNORECASE):
        return "etf_or_stock"
    return "stock"

def passes_liquidity(meta_row: dict, min_volume: int = 10000) -> bool:
    vol = meta_row.get("avg_daily_volume") or 0
    try:
        return int(vol) >= int(min_volume)
    except Exception:
        return False
