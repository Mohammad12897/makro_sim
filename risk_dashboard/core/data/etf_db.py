#core/data/etf_db.py
import json
from pathlib import Path

def load_etf_db():
    path = Path(__file__).with_name("etf_database.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_etf_tickers():
    return [e["ticker"] for e in load_etf_db()]
