# core/data/etf.py

def get_etf_metrics(ticker: str) -> dict:
    """
    Liefert ETF-Kennzahlen für das Radar.
    Nutzt die interne ETF-Datenbank (load_etf_db).
    """

    from core.data.db import load_etf_db

    db = load_etf_db()
    entry = next((e for e in db if e["ticker"] == ticker), None)

    if not entry:
        return {
            "1Y %": None,
            "5Y %": None,
            "Volatilität %": None,
            "Sharpe": None,
            "TER": None,
            "Tracking Error": None,
            "AUM": None,
            "DivRendite %": None,
        }

    return {
        "1Y %": entry.get("1Y %"),
        "5Y %": entry.get("5Y %"),
        "Volatilität %": entry.get("Volatilität %"),
        "Sharpe": entry.get("Sharpe"),
        "TER": entry.get("TER"),
        "Tracking Error": entry.get("Tracking Error"),
        "AUM": entry.get("AUM"),
        "DivRendite %": entry.get("DivRendite %"),
    }

