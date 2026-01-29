# core/ui_helpers.py
from typing import List, Dict
from core.data.etf_db_loader import load_etf_db
from core.data.country_to_region import country_to_region

def countries_with_etfs(countries: List[str]) -> Dict[str, Dict]:
    """
    Für jede Country-String in 'countries' gibt die Funktion:
      {country: {"tickers": [...], "count": n, "region": region}}
    zurück. Leere Liste bedeutet keine ETFs in der DB.
    """
    db = load_etf_db()
    result = {}
    for country in countries:
        key = country.strip().lower()
        region = country_to_region.get(key)
        if region is None:
            # heuristische Fallbacks
            if any(k in key for k in ("deutsch", "germ", "frank", "brit", "uk")):
                region = "Europa"
            elif any(k in key for k in ("us", "america")):
                region = "USA"
            elif "jap" in key:
                region = "Asien"
            else:
                region = "Global"

        tickers = [e["ticker"] for e in db if e.get("region","").strip().lower() == region.strip().lower()]
        result[country] = {"tickers": tickers, "count": len(tickers), "region": region}
    return result
