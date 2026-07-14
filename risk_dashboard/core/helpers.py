# risk_dashboard/core/helpers.py
from typing import Tuple

def classify_etf(etf: str) -> Tuple[str, str]:
    if etf.startswith(("CSPX", "EQQQ")):
        return ("iShares", "UK‑/US‑Anbieter (BlackRock). Echte Holdings verfügbar über iShares‑CSV.")
    if etf.startswith(("VUAA", "VWRL")):
        return ("Vanguard", "US‑Anbieter. Keine iShares‑CSV, Demo‑Holdings empfohlen.")
    if etf.startswith("XDAX"):
        return ("Xtrackers", "Deutsche DWS‑ETFs. Keine iShares‑CSV, Demo‑Holdings empfohlen.")
    if etf.startswith("FZ"):
        return ("Amundi", "Französischer Anbieter. Keine iShares‑CSV, Demo‑Holdings empfohlen.")
    if etf == "CASH":
        return ("Cash", "Barbestand oder Geldmarktposition, keine Holdings.")
    return ("Unbekannt", "Keine Zuordnung möglich. Demo‑Holdings empfohlen.")
