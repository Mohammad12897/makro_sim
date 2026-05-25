# save as scripts/find_duplicates.py and run: python scripts/find_duplicates.py
# https://finance.yahoo.com/quote/EXS1.DE
import yaml
from collections import defaultdict
p = "risk_dashboard/config/etf_universe.yaml"
with open(p, encoding="utf8") as f:
    data = yaml.safe_load(f)
by_ticker = defaultdict(list)
by_isin = defaultdict(list)
for key, val in (data or {}).items():
    t = val.get("ticker")
    i = val.get("isin")
    by_ticker[t].append(key)
    by_isin[i].append(key)
print("Duplicate tickers:")
for t, keys in by_ticker.items():
    if len(keys) > 1:
        print(t, "->", keys)
print("\nDuplicate ISINs:")
for i, keys in by_isin.items():
    if len(keys) > 1:
        print(i, "->", keys)
