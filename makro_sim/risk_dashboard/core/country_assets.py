# country_assets.py
import numpy as np

# ---------------------------
# Hilfsfunktionen / Mappings
# ---------------------------

def compute_risk_scores(preset: dict) -> dict:
    """
    Erwartet ein preset mit Rohwerten (0..1) oder skaliertem Input.
    Liefert standardisierte Scores: political_security, strategische_autonomie, total
    """
    # Beispiel: preset enthält keys 'political_security', 'strategic_autonomy', 'total'
    ps = float(preset.get("political_security", 0.5))
    aut = float(preset.get("strategic_autonomy", 0.5))
    total = float(preset.get("total", (ps + (1-aut)) / 2))
    # Clamp 0..1
    ps = max(0.0, min(1.0, ps))
    aut = max(0.0, min(1.0, aut))
    total = max(0.0, min(1.0, total))
    return {"political_security": ps, "strategische_autonomie": aut, "total": total}

# ---------------------------
# Staatsanleihen (YTM Schätzer)
# ---------------------------

def country_credit_spread_from_score(ps_score: float) -> float:
    """
    Einfaches lineares Mapping: ps_score in [0,1] -> spread in Dezimal (z.B. 0.001 = 0.1%)
    0 -> sehr kleiner Spread, 1 -> hoher Spread (z.B. 8%)
    """
    base = 0.001  # 0.1%
    max_spread = 0.08  # 8%
    return base + ps_score * max_spread

def political_premium(ps_score: float) -> float:
    """
    Zusätzlicher politischer Aufschlag (bis z.B. 2%)
    """
    return ps_score * 0.02

def sovereign_ytm(rf_yield: float, ps_score: float) -> float:
    """
    Schätzt eine erwartete YTM für Staatsanleihen des Landes.
    rf_yield: risikofreier Zinssatz (z.B. 10y Treasury/Bund) in Dezimal
    ps_score: politisches Risiko (0..1)
    """
    spread = country_credit_spread_from_score(ps_score)
    pol = political_premium(ps_score)
    return rf_yield + spread + pol

# ---------------------------
# Aktien (länderbezogen)
# ---------------------------

def country_equity_premium(total_score: float) -> float:
    """
    Länderrisikoaufschlag für Aktien (bis z.B. 6%)
    """
    return total_score * 0.06

def expected_equity_return(rf: float, beta: float, erp: float, total_score: float) -> float:
    """
    Erwartete Aktienrendite (vereinfachtes CAPM + country premium)
    rf: risikofreier Zinssatz
    beta: Markt-Beta (default ~1)
    erp: Equity Risk Premium (z.B. 0.05 = 5%)
    total_score: Gesamtrisiko (0..1)
    """
    return rf + beta * erp + country_equity_premium(total_score)

# ---------------------------
# Gold (länderbezogen)
# ---------------------------

def expected_gold_return(global_gold_premium: float, fx_change: float, ps_score: float) -> float:
    """
    Erwartete Goldrendite lokal:
    - global_gold_premium: erwartete globale Goldrendite (z.B. 0.03)
    - fx_change: erwartete Währungsbewegung (positiv = lokale Währung schwächt sich)
    - ps_score: politisches Risiko -> leichter Aufschlag
    """
    return global_gold_premium + fx_change + ps_score * 0.01

# ---------------------------
# ETF Mapping & Investment Profile
# ---------------------------

def etf_mapping_for_cluster(cid: int) -> str:
    if cid == 2:
        return (
            "### ETF-Mapping für Cluster 2 (niedriges Risiko)\n"
            "- Industrieländer-ETFs\n"
            "- Infrastruktur-ETFs\n"
            "- Qualitätsaktien-ETFs\n"
            "- Staatsanleihen hoher Bonität\n"
        )
    elif cid == 1:
        return (
            "### ETF-Mapping für Cluster 1 (mittleres Risiko)\n"
            "- Emerging-Markets-ETFs\n"
            "- Rohstoff-ETFs\n"
            "- Branchen-ETFs (Industrie, Energie)\n"
        )
    else:
        return (
            "### ETF-Mapping für Cluster 0 (hohes Risiko)\n"
            "- Frontier-Markets-ETFs (kleiner Anteil)\n"
            "- Rohstoff-Exposure\n"
            "- Themen-ETFs (taktisch)\n"
        )

def investment_profile_for_cluster(ps: float, aut: float, total: float) -> str:
    lines = []
    if total < 0.4 and ps < 0.3 and aut > 0.7:
        titel = "Resiliente, autonome Staaten (niedriges Gesamtrisiko)"
        lines.append("- Aktien: geeignet für langfristiges Wachstum (breite ETFs, Blue Chips).")
        lines.append("- Staatsanleihen: hohe Bonität, stabile Kupons.")
        lines.append("- Gold: als Diversifikation möglich, aber nicht zwingend notwendig.")
    elif total < 0.6:
        titel = "Staaten mit mittlerem Risiko (Schwellenländer-Profil)"
        lines.append("- Aktien: Emerging-Markets-ETFs, Branchen-ETFs.")
        lines.append("- Staatsanleihen: mittlere Bonität, höhere Kupons, höheres Risiko.")
        lines.append("- Gold: sinnvoll als Stabilitätsanker.")
    else:
        titel = "Verwundbare Staaten (hohes Gesamtrisiko)"
        lines.append("- Aktien: nur selektiv, hohe Volatilität.")
        lines.append("- Staatsanleihen: hohes Ausfallrisiko, nur taktisch.")
        lines.append("- Gold: wichtig als Absicherung gegen politische Risiken.")

    if aut > 0.7:
        lines.append("- Hohe Autonomie: geringere geopolitische Abhängigkeit.")
    elif aut < 0.3:
        lines.append("- Geringe Autonomie: hohe Abhängigkeit von externen Akteuren.")
    else:
        lines.append("- Mittlere Autonomie: gemischtes Profil.")

    if ps > 0.7:
        lines.append("- Hohes politisches Risiko: erhöhte Gefahr von Schocks.")
    elif ps < 0.3:
        lines.append("- Niedriges politisches Risiko: stabile Rahmenbedingungen.")
    else:
        lines.append("- Mittleres politisches Risiko: gewisse Unsicherheiten.")

    md = f"### {titel}\n\n" + "\n".join(lines)
    return md

# ---------------------------
# Länderbezogene Asset-Erwartungen
# ---------------------------

def compute_country_asset_expectations(land: str, presets: dict,
                                       rf_yield_global: float = 0.02,
                                       erp: float = 0.05,
                                       global_gold_premium: float = 0.03,
                                       fx_expectation: float = 0.0,
                                       beta: float = 1.0) -> dict:
    """
    Liefert erwartete Renditen (dezimal) für Equity, Bonds, Gold für ein Land.
    presets: dict mit Länderdaten (muss compute_risk_scores unterstützen)
    """
    if land not in presets:
        raise KeyError(f"Land '{land}' nicht in presets.")

    scores = compute_risk_scores(presets[land])
    ps = scores["political_security"]
    total = scores["total"]

    bond_yield = sovereign_ytm(rf_yield_global, ps)
    equity_mu = expected_equity_return(rf_yield_global, beta, erp, total)
    gold_mu = expected_gold_return(global_gold_premium, fx_expectation, ps)

    return {
        "equity_mu": equity_mu,
        "bond_yield": bond_yield,
        "gold_mu": gold_mu,
        "scores": scores
    }

# ---------------------------
# Portfolio-Metriken & Monte Carlo
# ---------------------------

def portfolio_metrics(weights: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float = 0.0) -> dict:
    """
    weights: array-like (n,)
    mu: expected returns (n,)
    cov: covariance matrix (n,n)
    """
    w = np.array(weights, dtype=float)
    w = w / w.sum() if w.sum() != 0 else w
    mu_p = float(w.dot(mu))
    sigma_p = float(np.sqrt(w.dot(cov).dot(w)))
    sharpe = (mu_p - rf) / sigma_p if sigma_p > 0 else np.nan
    return {"mu": mu_p, "sigma": sigma_p, "sharpe": sharpe}

def monte_carlo_portfolio(weights: np.ndarray, mu: np.ndarray, cov: np.ndarray, n: int = 10000, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    sims = rng.multivariate_normal(mu, cov, size=n)
    port_returns = sims.dot(weights)
    var95 = np.percentile(port_returns, 5)
    cvar95 = port_returns[port_returns <= var95].mean() if np.any(port_returns <= var95) else var95
    return {"sim_mean": float(port_returns.mean()), "var95": float(var95), "cvar95": float(cvar95), "sim_returns": port_returns}

# ---------------------------
# Beispiel-Helper: Erzeuge Kovarianzmatrix aus Volatilitäten und Korrelation
# ---------------------------

def build_cov_matrix(vols: np.ndarray, corr: np.ndarray = None) -> np.ndarray:
    """
    vols: array of volatilities (std dev) per asset (annual)
    corr: correlation matrix (n,n) or None -> identity
    """
    vols = np.array(vols, dtype=float)
    n = len(vols)
    if corr is None:
        corr = np.eye(n)
    cov = np.outer(vols, vols) * np.array(corr)
    return cov
