# core/ews.py

from __future__ import annotations
from typing import Dict
from risk_dashboard.core.risk_model import compute_risk_scores


# ---------------------------------------------------------
# Ampel-Logik fÃ¼r einzelne Dimensionen
# ---------------------------------------------------------

def risk_level(value: float) -> str:
    if value < 0.33:
        return "ðŸŸ¢ stabil"
    elif value < 0.66:
        return "ðŸŸ¡ Warnung"
    else:
        return "ðŸ”´ kritisch"


# ---------------------------------------------------------
# Early-Warning-System (EWS)
# ---------------------------------------------------------

def ews_from_scores(scores: Dict[str, float]) -> str:
    """
    Erzeugt eine textuelle FrÃ¼hwarnanalyse basierend auf allen Risiko-Dimensionen.
    EnthÃ¤lt:
    - Ampel fÃ¼r jede Dimension
    - Sonderwarnung fÃ¼r politische AbhÃ¤ngigkeit
    - Bewertung der strategischen Autonomie
    - Gesamtfazit
    """
    md = "# ðŸš¨ Early-Warning-System (EWS)\n\n"

    # -----------------------------------------------------
    # Dimensionen durchgehen
    # -----------------------------------------------------
    md += "## ðŸ“Š Risiko-Ampeln\n"

    for dim, value in scores.items():
        if dim == "total":
            continue
        md += f"- **{dim}**: {risk_level(value)} ({value:.2f})\n"

    # -----------------------------------------------------
    # Sonderwarnung: politische AbhÃ¤ngigkeit
    # -----------------------------------------------------
    ps = scores["political_security"]

    if ps > 0.75:
        md += (
            "\n## âš ï¸ Spezielle Warnung: Politische AbhÃ¤ngigkeit\n"
            "- Hohe politische AbhÃ¤ngigkeit kann die **strategische Autonomie massiv einschrÃ¤nken**.\n"
            f"- Aktueller Wert: **{ps:.2f}**\n"
        )
    elif ps > 0.55:
        md += (
            "\n## âš ï¸ Hinweis: ErhÃ¶hte politische AbhÃ¤ngigkeit\n"
            "- Politische AbhÃ¤ngigkeiten sollten beobachtet und reduziert werden.\n"
            f"- Aktueller Wert: **{ps:.2f}**\n"
        )

    # -----------------------------------------------------
    # Bewertung der strategischen Autonomie
    # -----------------------------------------------------
    sa = scores["strategische_autonomie"]

    md += "\n## ðŸ›¡ Strategische Autonomie\n"

    if sa > 0.75:
        md += "- Die strategische Autonomie ist **sehr hoch** â€“ das Land kann souverÃ¤n handeln.\n"
    elif sa > 0.50:
        md += "- Die strategische Autonomie ist **solide**, aber nicht vollstÃ¤ndig.\n"
    else:
        md += "- Die strategische Autonomie ist **eingeschrÃ¤nkt** â€“ externe Akteure beeinflussen Entscheidungen.\n"

    md += f"- Autonomie-Score: **{sa:.2f}**\n"

    # -----------------------------------------------------
    # Gesamtfazit
    # -----------------------------------------------------
    total = scores["total"]

    md += "\n## ðŸ§¾ Gesamtfazit\n"

    if total > 0.75:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** â†’ **ðŸ”´ kritisch**.\n"
            "- Sofortige MaÃŸnahmen zur Risikoreduktion erforderlich.\n"
        )
    elif total > 0.55:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** â†’ **ðŸŸ¡ erhÃ¶hte Risikolage**.\n"
            "- Engmaschiges Monitoring empfohlen.\n"
        )
    else:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** â†’ **ðŸŸ¢ stabil**.\n"
            "- Keine akute GefÃ¤hrdung, aber regelmÃ¤ÃŸige ÃœberprÃ¼fung sinnvoll.\n"
        )

    return md


# ---------------------------------------------------------
# Hauptfunktion: EWS fÃ¼r ein Land
# ---------------------------------------------------------

def ews_for_country(country: str, params: Dict) -> str:
    """
    Berechnet das EWS fÃ¼r ein bestimmtes Land.
    """
    scores = compute_risk_scores(params)
    return ews_from_scores(scores)

