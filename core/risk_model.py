# core/risk_model.py

from __future__ import annotations
from typing import Dict, Tuple
import math

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def normalize_exp(x, scale=1.0):
    """Exponentielle Normalisierung: hohe Werte wirken überproportional riskant."""
    return clamp01(1 - math.exp(-x / scale))

def normalize_log(x, max_val=20.0):
    """Logarithmische Normalisierung: Reserven wirken stark risikomindernd."""
    return clamp01(1 - (math.log1p(x) / math.log1p(max_val)))

def compute_risk_scores(p: dict) -> Dict[str, float]:
    # 1) MAKRO-RISIKO (40 %)
    versch = p.get("verschuldung", 0.8)
    fx = p.get("FX_Schockempfindlichkeit", 0.8)
    res = p.get("Reserven_Monate", 6)

    versch_norm = normalize_exp(versch, scale=1.0)
    fx_norm = clamp01(fx / 2.0)
    res_norm = normalize_log(res, max_val=20.0)

    macro = (
        0.5 * versch_norm +
        0.3 * fx_norm +
        0.2 * res_norm
    )

    # 2) GEO-RISIKO (35 %)
    usd = p.get("USD_Dominanz", 0.7)
    sank = p.get("Sanktions_Exposure", 0.05)
    alt = p.get("Alternativnetz_Abdeckung", 0.5)

    usd_norm = clamp01(usd)
    sank_norm = clamp01(sank * 2.0)
    alt_norm = clamp01(alt)

    geo = (
        0.4 * usd_norm +
        0.4 * sank_norm +
        0.2 * ((1 - alt_norm) ** 1.5)
    )

    # 3) GOVERNANCE-RISIKO (25 %)
    demo = p.get("demokratie", 0.8)
    innov = p.get("innovation", 0.6)
    fach = p.get("fachkraefte", 0.7)
    korr = p.get("korruption", 0.3)

    gov = (
        0.45 * (1 - clamp01(demo)) +
        0.30 * clamp01(korr) +
        0.15 * (1 - clamp01(innov)) +
        0.10 * (1 - clamp01(fach))
    )

    # 4) HANDELS-RISIKO (neu)
    export_konz = p.get("export_konzentration", 0.5)
    import_krit = p.get("import_kritische_gueter", 0.5)
    partner_konz = p.get("partner_konzentration", 0.5)

    handel = (
        0.4 * clamp01(export_konz) +
        0.3 * clamp01(import_krit) +
        0.3 * clamp01(partner_konz)
    )

    # 5) GESAMTRISIKO (Handel integriert)
    total = (
        0.35 * macro +
        0.30 * geo +
        0.20 * gov +
        0.15 * handel
    )

    # 6) Zusatzdimensionen (für Radar)
    finanz = clamp01((versch / 2.0 + fx / 2.0))
    sozial = clamp01((1 - fach) * 0.5 + (1 - demo) * 0.5)

    return {
        "macro": clamp01(macro),
        "geo": clamp01(geo),
        "governance": clamp01(gov),
        "handel": clamp01(handel),
        "finanz": finanz,
        "sozial": sozial,
        "total": clamp01(total),
    }
    
def risk_category(score: float) -> Tuple[str, str]:
    if score < 0.33:
        return "stabil", "green"
    elif score < 0.66:
        return "warnung", "yellow"
    else:
        return "kritisch", "red"
