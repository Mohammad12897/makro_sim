#core/data/etf_db_loader.py
import json
from pathlib import Path
from core.data.ticker_validation import validate_or_fix_ticker

def load_etf_db():
    path = Path(__file__).with_name("etf_database.json")
    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    valid_entries = []
    for etf in db:
        ticker = etf["ticker"]
        fixed = validate_or_fix_ticker(ticker)

        if fixed is None:
            # ETF komplett ignorieren
            continue

        etf["ticker"] = fixed
        valid_entries.append(etf)

    return valid_entries

def list_etf_tickers():
    return [e["ticker"] for e in load_etf_db()]
