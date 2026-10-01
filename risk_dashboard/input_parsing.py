# risk_dashboard/input_parsing.py
import re
from typing import Dict, List, Tuple

TICKER_QTY_RE = re.compile(r'^\s*([A-Za-z0-9\.\-]+)\s*(?:[:=,\s]\s*(\d+))?\s*$')

def parse_ticker_input(raw: str, default_qty: int = 1) -> Tuple[Dict[str,int], List[str]]:
    """
    Parsen von Eingaben wie:
      - "DAX 3"
      - "BTC:3"
      - "DAX:1, BTC:2, NVDA 5"
      - Zeilenweise
      - "DAX, BTC"  -> Menge = default_qty
    Rückgabe:
      - dict {TICKER: quantity}
      - list invalid_entries
    """
    if not raw or not raw.strip():
        return {}, []

    parts: List[str] = []
    if '\n' in raw:
        parts = [p.strip() for p in raw.splitlines() if p.strip()]
    elif ',' in raw:
        parts = [p.strip() for p in raw.split(',') if p.strip()]
    else:
        tokens = raw.split()
        if len(tokens) <= 2:
            parts = [' '.join(tokens)]
        else:
            i = 0
            while i < len(tokens):
                if i+1 < len(tokens) and tokens[i+1].isdigit():
                    parts.append(f"{tokens[i]} {tokens[i+1]}")
                    i += 2
                else:
                    parts.append(tokens[i])
                    i += 1

    result: Dict[str,int] = {}
    invalid: List[str] = []
    for p in parts:
        m = TICKER_QTY_RE.match(p)
        if not m:
            invalid.append(p)
            continue
        ticker = m.group(1).upper()
        qty = m.group(2)
        qty_val = int(qty) if qty is not None else default_qty
        if qty_val < 0:
            invalid.append(p)
            continue
        result[ticker] = result.get(ticker, 0) + qty_val

    return result, invalid
