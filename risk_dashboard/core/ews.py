# core/ews.py

from __future__ import annotations
from typing import Dict
from risk_dashboard.core.risk_model import compute_risk_scores


# ---------------------------------------------------------
# Ampel-Logik für einzelne Dimensionen
# ---------------------------------------------------------

def risk_level(value: float) -> str:
    if value < 0.33:
        return "🟢 stabil"
    elif value < 0.66:
        return "🟡 Warnung"
    else:
        return "🔴 kritisch"


# ---------------------------------------------------------
# Early-Warning-System (EWS)
# ---------------------------------------------------------

def ews_from_scores(scores: Dict[str, float]) -> str:
    """
    Erzeugt eine textuelle Frühwarnanalyse basierend auf allen Risiko-Dimensionen.
    Enthält:
    - Ampel für jede Dimension
    - Sonderwarnung für politische Abhängigkeit
    - Bewertung der strategischen Autonomie
    - Gesamtfazit
    """
    md = "# 🚀 Early‑Warning‑System (EWS)\n\n"

    # -----------------------------------------------------
    # Dimensionen durchgehen
    # -----------------------------------------------------
    md += "## 📊 Risiko‑Ampeln\n"


    for dim, value in scores.items():
        if dim == "total":
            continue
        md += f"- **{dim}**: {risk_level(value)} ({value:.2f})\n"

    # -----------------------------------------------------
    # Sonderwarnung: politische Abhängigkeit
    # -----------------------------------------------------
    ps = scores["political_security"]

    if ps > 0.75:
        md += (
        "\n## ⚠️ Spezielle Warnung: Politische Abhängigkeit\n"
        "- Hohe politische Abhängigkeit kann die **strategische Autonomie massiv einschränken**.\n"
        f"- Aktueller Wert: **{ps:.2f}**\n"
        )
    elif ps > 0.55:
        md += (
            "\n## ℹ️ Hinweis: Erhöhte politische Abhängigkeit\n"
            "- Politische Abhängigkeiten sollten beobachtet und reduziert werden.\n"
            f"- Aktueller Wert: **{ps:.2f}**\n"
        )

    # -----------------------------------------------------
    # Bewertung der strategischen Autonomie
    # -----------------------------------------------------
    sa = scores["strategische_autonomie"]

    md += "\n## ⚖️ Strategische Autonomie\n"

    if sa > 0.75:
        md += "- Die strategische Autonomie ist **sehr hoch** → das Land kann souverän handeln.\n"
    elif sa > 0.50:
        md += "- Die strategische Autonomie ist **solide**, aber nicht vollständig.\n"
    else:
        md += "- Die strategische Autonomie ist **eingeschränkt** → externe Akteure beeinflussen Entscheidungen.\n"

    md += f"- Autonomie-Score: **{sa:.2f}**\n"

    # -----------------------------------------------------
    # Gesamtfazit
    # -----------------------------------------------------
    total = scores["total"]

    md += "\n## 🧾 Gesamtfazit\n"

    if total > 0.75:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** → **🔴 kritisch**.\n"
            "- Sofortige Maßnahmen zur Risikoreduktion erforderlich.\n"
        )
    elif total > 0.55:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** → **🟡 erhöhte Risikolage**.\n"
            "- Engmaschiges Monitoring empfohlen.\n"
        )
    else:
        md += (
            f"- Das Gesamtrisiko liegt bei **{total:.2f}** → **🟢 stabil**.\n"
            "- Keine akute Gefährdung, aber regelmäßige Überprüfung sinnvoll.\n"
        )

    return md


# ---------------------------------------------------------
# Hauptfunktion: EWS für ein Land
# ---------------------------------------------------------

def ews_for_country(country: str, params: Dict) -> str:
    """
    Berechnet das EWS für ein bestimmtes Land.
    """
    scores = compute_risk_scores(params)
    return ews_from_scores(scores)

