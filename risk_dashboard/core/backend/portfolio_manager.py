# core/backend/portfolio_manager.py
import json
from pathlib import Path
import pandas as pd
from core.data.logging import logger

# WICHTIG: genau dieser Pfad, damit Radar, Backtest, Vergleich alle dieselbe Datei sehen
PORTFOLIO_FILE = Path("core/data/portfolios.json")

def _load_all():
    if not PORTFOLIO_FILE.exists():
        return []
    try:
        return json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error loading portfolios: {e}")
        return []

def _save_all(portfolios):
    PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_FILE.write_text(json.dumps(portfolios, indent=2), encoding="utf-8")

def list_portfolios():
    return _load_all()

def save_portfolio(name, symbols, weights, meta=None):
    weights = [float(w) for w in weights]
    total = sum(weights)
    if total == 0:
        weights = [1/len(weights)] * len(weights)
    else:
        weights = [w/total for w in weights]

    portfolios = _load_all()
    portfolios = [p for p in portfolios if p["name"] != name]
    portfolios.append({
        "name": name,
        "symbols": symbols,
        "weights": weights,
        "meta": meta or {}
    })
    _save_all(portfolios)
    return f"Portfolio '{name}' gespeichert."

def delete_portfolio(name):
    portfolios = _load_all()
    before = len(portfolios)
    portfolios = [p for p in portfolios if p["name"] != name]
    _save_all(portfolios)
    if len(portfolios) < before:
        return f"Portfolio '{name}' gelöscht."
    return f"Portfolio '{name}' nicht gefunden."

def get_portfolio(name):
    portfolios = _load_all()
    for p in portfolios:
        if p["name"] == name:
            df = pd.DataFrame({"symbol": p["symbols"], "weight": p["weights"]})
            return df, p
    return None, None
