import re
from typing import List, Dict

_QUICK_ADD_PATTERN = re.compile(
    r"""
    (?P<ticker>[A-Za-z0-9\.\-_]+)
    (?:\s*[:\s]\s*
    (?P<qty>-?\d+(\.\d+)?))?
    """,
    re.VERBOSE,
)

def parse_quick_add(text: str, default_qty: int = 1) -> List[Dict]:
    if not text:
        return []

    normalized = re.sub(r'[\r\n;]+', ',', text.strip())
    parts = [p.strip() for p in normalized.split(',') if p.strip()]

    results = []
    for part in parts:
        m = _QUICK_ADD_PATTERN.match(part)
        if not m:
            tokens = part.split()
            if len(tokens) == 1:
                ticker = tokens[0].upper()
                qty = default_qty
            elif len(tokens) >= 2:
                ticker = tokens[0].upper()
                try:
                    qty = int(float(tokens[1]))
                except Exception:
                    qty = default_qty
            else:
                continue
        else:
            ticker = m.group("ticker").upper()
            qty_raw = m.group("qty")
            if qty_raw is None:
                qty = default_qty
            else:
                try:
                    qty = int(float(qty_raw))
                except Exception:
                    qty = default_qty

        if qty < 0:
            qty = default_qty
        results.append({"ticker": ticker, "quantity": qty})

    return results
