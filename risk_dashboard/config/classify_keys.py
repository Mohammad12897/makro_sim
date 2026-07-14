# classify_keys.py
# python .\risk_dashboard/config\classify_keys.py
import os, yaml, ast, csv
import logging

logger = logging.getLogger(__name__)

YAML_PATH = "risk_dashboard/config/etf_universe.yaml"
PY_PATH = "risk_dashboard/config/etf_candidates.py"
OUT_CSV = "key_classification.csv"

def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf8") as f:
        data = yaml.safe_load(f) or {}
    # entpacke Wrapper wie "etf_universe:"
    if isinstance(data, dict) and len(data) == 1:
        first_val = next(iter(data.values()))
        if isinstance(first_val, dict):
            return first_val
    return data

def load_py_dict(path):
    if not os.path.exists(path):
        return {}
    src = open(path, "r", encoding="utf8").read()
    try:
        starts = [i for i,c in enumerate(src) if c == "{"]
        ends = [i for i,c in enumerate(src) if c == "}"]
        if not starts or not ends:
            return {}
        start = starts[0]
        end = ends[-1] + 1
        snippet = src[start:end]
        data = ast.literal_eval(snippet)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def classify_entry(key, meta):
    if not isinstance(meta, dict):
        return "Unknown", "no metadata"
    # Custom / Paket
    if "components" in meta and isinstance(meta["components"], dict):
        return "Custom", "has components"
    # klare Asset Class Hinweise
    asset = (meta.get("asset_class") or "").lower()
    ticker = (meta.get("ticker") or "").upper()
    has_rep = bool(meta.get("replication"))
    has_aum = bool(meta.get("aum"))
    ter = meta.get("ter_pct") if meta.get("ter_pct") is not None else meta.get("expense_ratio")
    # ETF Regeln
    if has_rep or has_aum:
        return "ETF", "has replication or aum"
    if ter is not None:
        try:
            ter_val = float(ter)
        except Exception:
            ter_val = None
        if ter_val is not None and ter_val > 0:
            return "ETF", "ter > 0"
    if asset in ("bond","cash"):
        return "ETF", "asset_class indicates bond/cash ETF"
    # Stock Regeln
    known_stock_tickers = {"AAPL","MSFT","AMZN","NVDA","SIE.DE"}
    if asset == "stock" or ticker in known_stock_tickers:
        return "Stock", "explicit stock asset_class or known ticker"
    # Fallback: wenn asset==equity und keine ETF‑Metadaten vorhanden -> Stock
    if asset == "equity" and not (has_rep or has_aum or (ter is not None and float(ter or 0) > 0)):
        return "Stock", "equity without ETF metadata -> treat as stock"
    # Sonst Unknown
    return "Unknown", "no decisive metadata"

def main():
    yaml_data = load_yaml(YAML_PATH)
    py_data = load_py_dict(PY_PATH)
    keys = {}
    for k,v in py_data.items():
        keys[k] = v
    for k,v in yaml_data.items():
        keys[k] = v
    rows = []
    for key, meta in keys.items():
        typ, reason = classify_entry(key, meta)
        ticker = meta.get("ticker") if isinstance(meta, dict) else ""
        name = meta.get("name") if isinstance(meta, dict) else ""
        rows.append({"key":key,"type":typ,"reason":reason,"ticker":ticker or "" ,"name": name or ""})
    with open(OUT_CSV, "w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=["key","type","reason","ticker","name"])
        writer.writeheader()
        writer.writerows(rows)
    logger.debug(f"Wrote {OUT_CSV} with {len(rows)} entries.")

if __name__ == "__main__":
    main()
