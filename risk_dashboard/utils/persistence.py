import json
import os
from typing import List

TICKER_STORE = ".cache/user_tickers.json"

def save_user_tickers(tickers: List[str]) -> None:
    os.makedirs(os.path.dirname(TICKER_STORE), exist_ok=True)
    try:
        with open(TICKER_STORE, "w", encoding="utf8") as f:
            json.dump(tickers, f)
    except Exception:
        # best effort, do not crash the app
        pass

def load_user_tickers() -> List[str]:
    if os.path.exists(TICKER_STORE):
        try:
            with open(TICKER_STORE, "r", encoding="utf8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
