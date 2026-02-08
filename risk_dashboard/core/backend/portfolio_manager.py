# core/backend/portfolio_manager.py
import json
from pathlib import Path
import pandas as pd
from core.data.logging import logger

PORTFOLIO_FILE = Path("data/portfolios.json")

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

def save_portfolio(name: str, symbols: list[str], weights: list[float], meta: dict | None = None):
    portfolios = _load_all()
    weights = [float(w) for w in weights]
    total = sum(weights)
    if total == 0:
        weights = [1/len(weights)] * len(weights)
    else:
        weights = [w/total for w in weights]

    new_port = {
        "name": name,
        "symbols": symbols,
        "weights": weights,
        "meta": meta or {}
    }

    portfolios = [p for p in portfolios if p["name"] != name]
    portfolios.append(new_port)
    _save_all(portfolios)
    return f"Portfolio '{name}' gespeichert."

def delete_portfolio(name: str):
    portfolios = _load_all()
    before = len(portfolios)
    portfolios = [p for p in portfolios if p["name"] != name]
    _save_all(portfolios)
    if len(portfolios) < before:
        return f"Portfolio '{name}' gelöscht."
    return f"Portfolio '{name}' nicht gefunden."

def get_portfolio(name: str):
    portfolios = _load_all()
    for p in portfolios:
        if p["name"] == name:
            df = pd.DataFrame({"symbol": p["symbols"], "weight": p["weights"]})
            return df, p
    return pd.DataFrame({"Fehler": [f"Portfolio '{name}' nicht gefunden"]}), None
