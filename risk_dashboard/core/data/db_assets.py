# core/data/db_assets.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.engine.assets import (
    fetch_prices,
    compute_ki_score_from_prices,
    compute_radar_data,
)

ASSET_TEMPLATE = {
    "Ticker": None,
    "Yahoo": None,
    "ISIN": None,
    "Name": None,
    "Typ": None,
    "Region": None,
    "Sektor": None,
    "Land": None,

    # ETF-spezifisch
    "TER": None,
    "Volumen": None,
    "Replikation": None,
    "TD": None,

    # Aktien-spezifisch
    "KGV": None,
    "KUV": None,
    "PEG": None,
    "Debt/Equity": None,
    "Cashflow": None,
    "Wachstum": None,
}

def normalize_asset(asset, typ):
    normalized = ASSET_TEMPLATE.copy()
    normalized.update(asset)

    # WICHTIG: Yahoo fallback
    if not normalized.get("Yahoo"):
        normalized["Yahoo"] = normalized.get("Ticker")

    normalized["Typ"] = typ
    return normalized

ETF_DB: List[Dict[str, Any]] = [
    # --- Global / World ---

        )

    typ_text, color, asset, ki_score, radar = process_asset_input(ticker)
    html = render_type_html(typ_text, color)

    return html, asset, ki_score, radar