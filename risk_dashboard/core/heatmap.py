# core/heatmap.py

from __future__ import annotations
from typing import Dict, List

from risk_dashboard.core.risk_model import compute_risk_scores


# ---------------------------------------------------------
# Klassische Risiko-Heatmap
# ---------------------------------------------------------

def risk_heatmap(presets: Dict[str, dict]) -> List[List]:
    """
    Gibt eine Heatmap-Tabelle zurück:
    Land | macro | geo | governance | handel | supply_chain | financial | tech | energie | currency | political_security | total
    """
    rows = []

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append([
            land,
            round(scores["macro"], 3),
            round(scores["geo"], 3),
            round(scores["governance"], 3),
            round(scores["handel"], 3),
            round(scores["supply_chain"], 3),
            round(scores["financial"], 3),
            round(scores["tech"], 3),
            round(scores["energie"], 3),
            round(scores["currency"], 3),
            round(scores["political_security"], 3),
            round(scores["total"], 3)
        ])

    return rows


# ---------------------------------------------------------
# Politische Abhängigkeit â€“ Heatmap
# ---------------------------------------------------------

def political_heatmap(presets: Dict[str, dict]) -> List[List]:
    """
    Land | political_security | Ampel
    """
    rows = []

    for land, params in presets.items():
        ps = compute_risk_scores(params)["political_security"]

        if ps > 0.75:
            color = "ðŸ”´"
        elif ps > 0.55:
            color = "ðŸŸ¡"
        else:
            color = "ðŸŸ¢"

        rows.append([land, round(ps, 3), color])

    return rows


# ---------------------------------------------------------
# Strategische Autonomie â€“ Heatmap
# ---------------------------------------------------------

def autonomy_heatmap(presets: Dict[str, dict]) -> List[List]:
    """
    Land | strategische_autonomie | Ampel
    """
    rows = []

    for land, params in presets.items():
        sa = compute_risk_scores(params)["strategische_autonomie"]

        if sa > 0.75:
            color = "ðŸŸ¢"
        elif sa > 0.50:
            color = "ðŸŸ¡"
        else:
            color = "ðŸ”´"

        rows.append([land, round(sa, 3), color])

    return rows


# ---------------------------------------------------------
# Kombinierte Heatmap (political_security + strategische_autonomie)
# ---------------------------------------------------------

def combined_political_autonomy_heatmap(presets: Dict[str, dict]) -> List[List]:
    """
    Land | political_security | strategische_autonomie | Interpretation
    """
    rows = []

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        ps = scores["political_security"]
        sa = scores["strategische_autonomie"]

        if ps > 0.75 and sa < 0.50:
            interp = "⚠️ Hohe Abhängigkeit, geringe Autonomie"
        elif ps > 0.55 and sa < 0.50:
            interp = "🟡 Erhöhte Abhängigkeit, begrenzte Autonomie"
        elif ps < 0.55 and sa > 0.75:
            interp = "🟢 Geringe Abhängigkeit, hohe Autonomie"
        else:
            interp = "➖ Ausgewogen"



        rows.append([
            land,
            round(ps, 3),
            round(sa, 3),
            interp
        ])

    return rows

