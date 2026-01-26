# core/scenario_engine.py

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Szenario-Konfiguration (leicht anpassbar)
# ---------------------------------------------------------

SCENARIO_CONFIG = {
    "Krise": {
        "mu_shift": np.array([-0.08, -0.02, 0.03]),   # equity, bonds, gold
        "cov_scale": 1.5,
        "corr_overwrite": None,
    },
    "Zinsanstieg": {
        "mu_shift": np.array([-0.02, 0.03, 0.00]),
        "cov_scale": 1.0,
        "corr_overwrite": {
            ("equity", "bonds"): -0.5,
        },
    },
    "Ölpreisschock": {
        "mu_shift": np.array([-0.03, 0.00, 0.05]),
        "cov_scale": 1.0,
        "corr_overwrite": {
            ("equity", "gold"): -0.5,
            ("bonds", "gold"): 1.2,
        },
    },
    "Keins": {
        "mu_shift": np.array([0.0, 0.0, 0.0]),
        "cov_scale": 1.0,
        "corr_overwrite": None,
    },
}

ASSETS = ["equity", "bonds", "gold"]


# ---------------------------------------------------------
# Dynamische Kovarianz pro Szenario
# ---------------------------------------------------------

def dynamic_covariance(base_cov: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    cov = base_cov.copy()
    cfg = SCENARIO_CONFIG.get(scenario_name, SCENARIO_CONFIG["Keins"])

    # globale Skalierung
    cov *= cfg["cov_scale"]

    # optionale Korrelation-Overrides
    corr_overwrite = cfg.get("corr_overwrite")
    if corr_overwrite:
        for (a1, a2), factor in corr_overwrite.items():
            if a1 in cov.index and a2 in cov.columns:
                cov.loc[a1, a2] *= factor
                cov.loc[a2, a1] *= factor

    return cov


# ---------------------------------------------------------
# Shock-Funktionen (array-basiert)
# mu: np.array([equity, bonds, gold])
# cov: np.ndarray oder DataFrame
# ---------------------------------------------------------

def crisis(mu, cov, t):
    cfg = SCENARIO_CONFIG["Krise"]
    mu = mu.copy() + cfg["mu_shift"]
    return mu, cov


def zinsanstieg(mu, cov, t):
    cfg = SCENARIO_CONFIG["Zinsanstieg"]
    mu = mu.copy() + cfg["mu_shift"]
    return mu, cov


def oil_shock(mu, cov, t):
    cfg = SCENARIO_CONFIG["Ölpreisschock"]
    mu = mu.copy() + cfg["mu_shift"]
    return mu, cov


def no_scenario(mu, cov, t):
    return mu, cov


# ---------------------------------------------------------
# Szenario-Dispatcher
# ---------------------------------------------------------

def scenario_by_name(name: str):
    if name == "Krise":
        return crisis
    if name == "Zinsanstieg":
        return zinsanstieg
    if name == "Ölpreisschock":
        return oil_shock
    return no_scenario


# ---------------------------------------------------------
# Radar-Overlay: Kennzahlen pro Szenario
# (Backend – Plot machst du in plots.py)
# ---------------------------------------------------------

def scenario_radar_metrics(land, presets, weights, years, run_portfolio_mc, mc_risk_metrics):
    """
    Liefert ein Dict: {szenario_name: metrics_dict}
    für Radar-Overlay (z.B. mean, std, sharpe, var95, max_drawdown).
    """
    scenarios = list(SCENARIO_CONFIG.keys())
    out = {}

    for scen in scenarios:
        sim, summary = run_portfolio_mc(
            land=land,
            presets=presets,
            w_equity=weights[0],
            w_bond=weights[1],
            w_gold=weights[2],
            years=years,
            scenario_name=scen,
        )
        m = mc_risk_metrics(sim)
        out[scen] = m

    return out
