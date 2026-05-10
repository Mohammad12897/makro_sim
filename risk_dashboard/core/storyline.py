# core/storyline.py

from __future__ import annotations
from typing import Dict
from core.risk_model import compute_risk_scores
from core.lexicon import load_lexicon



# ---------------------------------------------------------
# Hilfsfunktion: schÃ¶ne Namen fÃ¼r Dimensionen
# ---------------------------------------------------------

DIM_LABELS = {
    "macro": "MakroÃ¶konomisches Risiko",
    "geo": "Geopolitisches Risiko",
    "governance": "Governance & Institutionen",
    "handel": "HandelsabhÃ¤ngigkeit",
    "supply_chain": "Lieferkettenrisiko",
    "financial": "Finanzielle AbhÃ¤ngigkeit",
    "tech": "Technologische AbhÃ¤ngigkeit",
    "energie": "EnergieabhÃ¤ngigkeit",
    "currency": "WÃ¤hrungs- & ZahlungsabhÃ¤ngigkeit",
    "political_security": "Politische & sicherheitspolitische AbhÃ¤ngigkeit",
    "strategische_autonomie": "Strategische Autonomie",
    "total": "Gesamtrisiko"
}


def label(dimension: str) -> str:
    return DIM_LABELS.get(dimension, dimension)


# ---------------------------------------------------------
# Storyline 3.0 â€“ Hauptfunktion
# ---------------------------------------------------------

def storyline_v3(country: str, params: Dict) -> str:
    """
    Erzeugt eine narrative Risiko-Storyline fÃ¼r ein Land.
    """
    scores = compute_risk_scores(params)

    # Sortierung der Dimensionen
    dims_sorted = sorted(
        [(k, v) for k, v in scores.items() if k not in ("total")],
        key=lambda x: x[1],
        reverse=True
    )

    top = dims_sorted[:3]       # hÃ¶chste Risiken
    low = dims_sorted[-2:]      # stabilste Bereiche

    ps = scores["political_security"]
    sa = scores["strategische_autonomie"]

    md = f"# ðŸ§  Risiko-Storyline 3.0 â€“ {country}\n\n"

    # -----------------------------------------------------
    # Haupttreiber
    # -----------------------------------------------------
    md += "## ðŸ”¥ Haupttreiber des Risikos\n"
    for d, v in top:
        if d != "strategische_autonomie":
            md += f"- **{label(d)}**: {v:.2f}\n"

    # -----------------------------------------------------
    # StabilitÃ¤tsanker
    # -----------------------------------------------------
    md += "\n## ðŸŸ¢ StabilitÃ¤tsanker\n"
    for d, v in low:
        if d != "political_security":
            md += f"- **{label(d)}**: {v:.2f}\n"

    # -----------------------------------------------------
    # Politische AbhÃ¤ngigkeit & Autonomie
    # -----------------------------------------------------
    md += "\n## ðŸ›¡ Politische AbhÃ¤ngigkeit & Strategische Autonomie\n"

    # Politische AbhÃ¤ngigkeit
    if ps > 0.75:
        md += "- Das Land weist eine **kritisch hohe politische AbhÃ¤ngigkeit** auf.\n"
    elif ps > 0.55:
        md += "- Das Land zeigt eine **erhÃ¶hte politische AbhÃ¤ngigkeit**.\n"
    else:
        md += "- Die politische AbhÃ¤ngigkeit ist **moderat bis gering**.\n"

    # Strategische Autonomie
    if sa > 0.75:
        md += "- Die **strategische Autonomie** ist sehr hoch â€“ das Land kann souverÃ¤n handeln.\n"
    elif sa > 0.50:
        md += "- Die strategische Autonomie ist **solide**, aber nicht vollstÃ¤ndig.\n"
    else:
        md += "- Die strategische Autonomie ist **eingeschrÃ¤nkt** â€“ externe Akteure beeinflussen Entscheidungen.\n"

    # -----------------------------------------------------
    # Narrative Analyse
    # -----------------------------------------------------
    md += "\n## ðŸ“˜ Narrative Analyse\n"
    md += (
        "Die Risikoarchitektur des Landes zeigt ein komplexes Zusammenspiel aus wirtschaftlichen, "
        "geopolitischen und politischen Faktoren. Besonders prÃ¤gend sind die Dimensionen "
        f"**{label(top[0][0])}** und **{label(top[1][0])}**, die das Gesamtbild dominieren. "
        "Gleichzeitig wirken stabile Bereiche als Puffer gegen externe Schocks. "
        "Die Balance zwischen politischer AbhÃ¤ngigkeit und strategischer Autonomie bestimmt maÃŸgeblich "
        "die langfristige HandlungsfÃ¤higkeit des Landes.\n"
    )

    # -----------------------------------------------------
    # Handlungsempfehlungen
    # -----------------------------------------------------
    md += "\n## ðŸ›  Handlungsempfehlungen\n"
    md += "- Reduktion politischer AbhÃ¤ngigkeiten\n"
    md += "- Ausbau strategischer Autonomie (Diplomatie, Industrie, Energie)\n"
    md += "- Diversifikation kritischer AbhÃ¤ngigkeiten\n"
    md += "- StÃ¤rkung institutioneller Resilienz\n"
    md += "- Ausbau technologischer und finanzieller EigenstÃ¤ndigkeit\n"

    lex = load_lexicon()

    md += "## Kontext\n"
    md += f"Die Dimension **macro** bedeutet: {lex['macro']}\n\n"
    
    return md

