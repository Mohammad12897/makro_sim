# core/data/etf_db_loader.py
import json
from pathlib import Path
from functools import lru_cache

# Falls du eine eigene Validierungsfunktion hast, importiere sie hier.
# Stelle sicher, dass core/data/ticker_validation.py existiert und die Funktion liefert.
try:
    from core.data.ticker_validation import validate_or_fix_ticker
except Exception:
    # Fallback: einfache Identity-Funktion, falls Validierer fehlt.
    def validate_or_fix_ticker(ticker):
        return ticker if ticker and isinstance(ticker, str) else None

@lru_cache(maxsize=1)
def load_etf_db():
    """
    Lädt die Datei etf_database.json (im selben Verzeichnis) und validiert Ticker.
    Gibt eine Liste valider Einträge zurück.
    """
    path = Path(__file__).with_name("etf_database.json")
    if not path.exists():
        raise FileNotFoundError(f"ETF-Datenbank nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    valid_entries = []
    for etf in db:
        # Erwartete Keys: name, ticker, region, asset_class (falls nicht vorhanden, safe defaults)
        ticker = etf.get("ticker")
        fixed = validate_or_fix_ticker(ticker)

        if fixed is None:
            # ETF komplett ignorieren, wenn Ticker ungültig
            continue

        # Normalisiere Eintrag
        entry = {
            "name": etf.get("name", ""),
            "ticker": fixed,
            "region": etf.get("region", "Global"),
            "asset_class": etf.get("asset_class", "Equity")
        }
        valid_entries.append(entry)

    return valid_entries

def list_etf_tickers():
    """Gibt alle validierten Ticker als Liste zurück."""
    return [e["ticker"] for e in load_etf_db()]

def list_etf_by_region(region):
    """
    Gibt die Ticker-Liste für eine Region zurück.
    Erwartete region-Strings: 'Europa', 'USA', 'Global' (case-insensitive).
    Wenn region None oder unbekannt, wird 'Global' verwendet.
    """
    if not region:
        region = "Global"
    region_key = region.strip().lower()

    mapping = {
        "europa": "europa",
        "europe": "europa",
        "germany": "europa",
        "deutschland (dax)": "europa",
        "usa": "usa",
        "us": "usa",
        "united states": "usa",
        "global": "global",
        "world": "global"
    }

    # Normalisiere region auf unsere Kategorien
    normalized = mapping.get(region_key, None)
    if normalized is None:
        # Versuche einfache Heuristik: falls 'eu' in region -> Europa, 'us' -> USA, sonst Global
        if "eu" in region_key:
            normalized = "europa"
        elif "us" in region_key or "america" in region_key:
            normalized = "usa"
        else:
            normalized = "global"

    # Filtere DB
    db = load_etf_db()
    if normalized == "global":
        # Alle ETFs zurückgeben (oder optional nur solche mit region == 'Global')
        return [e["ticker"] for e in db]
    else:
        return [e["ticker"] for e in db if e.get("region", "").strip().lower() == normalized]

# Optional: kleine Hilfsfunktion, falls du Name->Ticker Lookup brauchst
def find_ticker_by_name(name):
    """Sucht Ticker anhand (Teil-)Name, gibt erste Treffer-Liste zurück."""
    if not name:
        return []
    name_key = name.strip().lower()
    return [e["ticker"] for e in load_etf_db() if name_key in e.get("name", "").lower()]
