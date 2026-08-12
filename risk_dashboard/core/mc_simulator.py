# core/mc_simulator.py
import numpy as np
import pandas as pd


def multi_period_mc(weights, mu, cov, years, n_paths=3000, rebalancing=True, shock_fn=None, seed=None):
    """
    Mehrperiodige Monte-Carlo-Simulation eines Portfolios.

    Parameters
    ----------
    weights : array-like
        Portfolio-Gewichte (z.B. [0.5, 0.3, 0.2]).
    mu : dict
        Erwartungswerte pro Asset-Klasse, z.B. {"equity": 0.06, "bonds": 0.02, "gold": 0.03}.
    cov : DataFrame
        Kovarianzmatrix (3x3).
    years : int
        Anzahl der Jahre.
    n_paths : int
        Anzahl der Simulationen.
    rebalancing : bool
        Ob jährlich rebalanciert wird.
    shock_fn : callable
        Funktion, die jährliche Schocks liefert (optional).
    seed : int
        Zufallsseed.

    Returns
    -------
    dict

    return pd.DataFrame(summary)