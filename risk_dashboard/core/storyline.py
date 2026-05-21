# core/storyline.py

from __future__ import annotations
from typing import Dict
from core.risk_model import compute_risk_scores
from core.lexicon import load_lexicon



# ---------------------------------------------------------
# Hilfsfunktion: schöne Namen für Dimensionen
# ---------------------------------------------------------

DIM_LABELS = {
    "macro": "Makroökonomisches Risiko",
    "geo": "Geopolitisches Risiko",
    "governance": "Governance & Institutionen",
    "handel": "Handelsabhängigkeit",
    "supply_chain": "Lieferkettenrisiko",
    "financial": "Finanzielle Abhängigkeit",
    "tech": "Technologische Abhängigkeit",
    "energie": "Energieabhängigkeit",
    "currency": "Währungs- & Zahlungsabhängigkeit",
    "political_security": "Politische & sicherheitspolitische Abhängigkeit",
    "strategische_autonomie": "Strategische Autonomie",
    "total": "Gesamtrisiko"
}


def label(dimension: str) -> str:
    return DIM_LABELS.get(dimension, dimension)


# ---------------------------------------------------------
# Storyline 3.0 - Hauptfunktion
# ---------------------------------------------------------

def storyline_v3(country: str, params: Dict) -> str:
    """
    Erzeugt eine narrative Risiko-Storyline für ein Land.
    """
    scores = compute_risk_scores(params)

    # Sortierung der Dimensionen
    dims_sorted = sorted(
        [(k, v) for k, v in scores.items() if k not in ("total")],
        key=lambda x: x[1],
        reverse=True
    )

    top = dims_sorted[:3]       # höchste Risiken
    low = dims_sorted[-2:]      # stabilste Bereiche

    ps = scores["political_security"]
    sa = scores["strategische_autonomie"]

    md = f"#Risiko-Storyline 3.0 - {country}\n\n"

    # -----------------------------------------------------
    # Haupttreiber
    # -----------------------------------------------------
    md += "##Haupttreiber des Risikos\n"
    for d, v in top:
        if d != "strategische_autonomie":
            md += f"- **{label(d)}**: {v:.2f}\n"

    # -----------------------------------------------------
    # Stabilitätsanker
    # -----------------------------------------------------
    md += "\n##Stabilitätsanker\n"
    for d, v in low:
        if d != "political_security":
            md += f"- **{label(d)}**: {v:.2f}\n"

    # -----------------------------------------------------
    # Politische Abhängigkeit & Autonomie
    # -----------------------------------------------------
    md += "\n##Politische Abhängigkeit & Strategische Autonomie\n"

    # Politische Abhängigkeit
    if ps > 0.75:
        md += "- Das Land weist eine **kritisch hohe politische Abhängigkeit** auf.\n"
    elif ps > 0.55:
        md += "- Das Land zeigt eine **erhöhte politische Abhängigkeit**.\n"
    else:
        md += "- Die politische Abhängigkeit ist **moderat bis gering**.\n"

    # Strategische Autonomie
    if sa > 0.75:
        md += "- Die **strategische Autonomie** ist sehr hoch - das Land kann souverän handeln.\n"
    elif sa > 0.50:
        md += "- Die strategische Autonomie ist **solide**, aber nicht vollständig.\n"
    else:
        md += "- Die strategische Autonomie ist **eingeschränkt** - externe Akteure beeinflussen Entscheidungen.\n"

    # -----------------------------------------------------
    # Narrative Analyse
    # -----------------------------------------------------
    md += "\n## ðŸ“˜ Narrative Analyse\n"
    md += (
        "Die Risikoarchitektur des Landes zeigt ein komplexes Zusammenspiel aus wirtschaftlichen, "
        "geopolitischen und politischen Faktoren. Besonders prägend sind die Dimensionen "
        f"**{label(top[0][0])}** und **{label(top[1][0])}**, die das Gesamtbild dominieren. "
        "Gleichzeitig wirken stabile Bereiche als Puffer gegen externe Schocks. "
        "Die Balance zwischen politischer Abhängigkeit und strategischer Autonomie bestimmt maßgeblich "
        "die langfristige Handlungsfähigkeit des Landes.\n"
    )

    # -----------------------------------------------------
    # Handlungsempfehlungen
    # -----------------------------------------------------
    md += "\n##Handlungsempfehlungen\n"
    md += "- Reduktion politischer Abhängigkeiten\n"
    md += "- Ausbau strategischer Autonomie (Diplomatie, Industrie, Energie)\n"
    md += "- Diversifikation kritischer Abhängigkeiten\n"
    md += "- Stärkung institutioneller Resilienz\n"
    md += "- Ausbau technologischer und finanzieller Eigenständigkeit\n"

    lex = load_lexicon()

    md += "## Kontext\n"
    md += f"Die Dimension **macro** bedeutet: {lex['macro']}\n\n"
    
    return md

