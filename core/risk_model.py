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

def tech_profile(scores: dict) -> str:
    t = scores["tech"]

    if t > 0.75:
        return "Sehr hohe technologische Abhängigkeit – kritische Verwundbarkeit."
    elif t > 0.55:
        return "Hohe technologische Abhängigkeit – Monitoring erforderlich."
    elif t > 0.35:
        return "Moderate technologische Abhängigkeit."
    else:
        return "Geringe technologische Abhängigkeit – robuste technologische Basis."

def compute_tech_dependency(p: dict) -> float:
    chips = p.get("halbleiter_abhaengigkeit", 0.5)
    software = p.get("software_cloud_abhaengigkeit", 0.5)
    ip = p.get("ip_lizenzen_abhaengigkeit", 0.5)
    keytech = p.get("schluesseltechnologie_importe", 0.5)

    risk = (
        0.35 * clamp01(chips) +
        0.30 * clamp01(software) +
        0.20 * clamp01(ip) +
        0.15 * clamp01(keytech)
    )
    return clamp01(risk)

def compute_supply_chain_risk(p: dict) -> float:
    chokepoint = p.get("chokepoint_abhaengigkeit", 0.5)
    jit = p.get("just_in_time_anteil", 0.5)
    konz = p.get("produktions_konzentration", 0.5)
    puffer = p.get("lager_puffer", 0.5)

    risk = (
        0.35 * clamp01(chokepoint) +
        0.30 * clamp01(jit) +
        0.25 * clamp01(konz) +
        0.10 * (1 - clamp01(puffer))
    )
    return clamp01(risk)


def compute_financial_dependency(p: dict) -> float:
    ausland = p.get("auslandsverschuldung", 0.5)
    kapital = p.get("kapitalmarkt_abhaengigkeit", 0.5)
    invest = p.get("investoren_anteil", 0.5)
    fx_refi = p.get("fremdwaehrungs_refinanzierung", 0.5)

    risk = (
        0.35 * clamp01(ausland) +
        0.25 * clamp01(kapital) +
        0.20 * clamp01(invest) +
        0.20 * clamp01(fx_refi)
    )
    return clamp01(risk)


def compute_risk_scores(p: dict) -> Dict[str, float]:
    # 1) MAKRO-RISIKO
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

    # 2) GEO-RISIKO
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

    # 3) GOVERNANCE-RISIKO
    demo = p.get("demokratie", 0.8)
    innov = p.get("innovation", 0.6)
    fach = p.get("fachkraefte", 0.7)
    korr = p.get("korruption", 0.3)

    governance = (
        0.45 * (1 - clamp01(demo)) +
        0.30 * clamp01(korr) +
        0.15 * (1 - clamp01(innov)) +
        0.10 * (1 - clamp01(fach))
    )

    # 4) HANDELS-RISIKO
    export_konz = p.get("export_konzentration", 0.5)
    import_krit = p.get("import_kritische_gueter", 0.5)
    partner_konz = p.get("partner_konzentration", 0.5)

    handel = (
        0.4 * clamp01(export_konz) +
        0.3 * clamp01(import_krit) +
        0.3 * clamp01(partner_konz)
    )

    # 5) Lieferketten-Risiko
    supply_chain = compute_supply_chain_risk(p)

    # 6) Finanzielle Abhängigkeit
    financial = compute_financial_dependency(p)

    # 7) Tech-Abhängigkeit
    tech = compute_tech_dependency(p)

    # 8) Energieabhängigkeit (NEU)
    energie = p.get("energie", 0.5)

    # 9) Währungs- & Zahlungsabhängigkeit (NEU)
    usd_dom = p.get("USD_Dominanz", 0.7)
    sank_exp = p.get("Sanktions_Exposure", 0.1)
    fx_sens = p.get("FX_Schockempfindlichkeit", 0.5)
    refi = p.get("fremdwaehrungs_refinanzierung", 0.5)
    kap_abh = p.get("kapitalmarkt_abhaengigkeit", 0.5)
    alt_net = p.get("Alternativnetz_Abdeckung", 0.5)

    currency = (
        0.30 * clamp01(usd_dom) +
        0.25 * clamp01(sank_exp * 2.0) +
        0.20 * clamp01(fx_sens / 2.0) +
        0.15 * clamp01(refi) +
        0.10 * clamp01(kap_abh) -
        0.10 * clamp01(alt_net)   # Alternativnetz reduziert Risiko
    )

    currency = clamp01(currency)



    # 10) GESAMTRISIKO
    total = (
        0.24 * macro +
        0.20 * geo +
        0.16 * governance +
        0.11 * handel +
        0.06 * supply_chain +
        0.07 * currency +
        0.06 * financial +
        0.05 * tech +
        0.05 * energie
    )

    return {
        "macro": macro,
        "geo": geo,
        "governance": governance,
        "handel": handel,
        "supply_chain": supply_chain,
        "financial": financial,
        "tech": tech,
        "energie": energie,
        "currency": currency,
        "total": total,
    }

def risk_category(score: float) -> Tuple[str, str]:
    if score < 0.33:
        return "stabil", "green"
    elif score < 0.66:
        return "warnung", "yellow"
    else:
        return "kritisch", "red"
