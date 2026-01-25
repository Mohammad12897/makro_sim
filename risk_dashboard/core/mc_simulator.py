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
        {
            "paths": np.array shape (n_paths, years),
            "terminal_distribution": np.array shape (n_paths,)
        }
    """

    rng = np.random.default_rng(seed)

    # Mean-Vektor in der richtigen Reihenfolge
    mu_vec = np.array([mu["equity"], mu["bonds"], mu["gold"]])

    cov_mat = cov.values
    n_assets = len(mu_vec)

    paths = np.zeros((n_paths, years))

    for p in range(n_paths):
        value = 1.0
        w = weights.copy()

        for t in range(years):
            # Schock anwenden
            if shock_fn is not None:
                mu_t, cov_t = shock_fn(mu_vec, cov_mat, t)
            else:
                mu_t, cov_t = mu_vec, cov_mat

            # Renditen simulieren
            ret = rng.multivariate_normal(mu_t, cov_t)

            # Portfolio-Rendite
            port_ret = np.dot(w, ret)
            value *= (1 + port_ret)

            paths[p, t] = value

            # Rebalancing
            if rebalancing:
                w = weights.copy()

    terminal = paths[:, -1]

    return {
        "paths": paths,
        "terminal_distribution": terminal,
    }


def summarize_paths(sim):
    """
    Aggregiert die MC-Pfade zu Jahresstatistiken.

    Returns DataFrame:
        year | mean | var95
    """
    paths = sim["paths"]
    years = paths.shape[1]

    summary = {
        "year": np.arange(1, years + 1),
        "mean": paths.mean(axis=0),
        "var95": np.percentile(paths, 5, axis=0),
    }

    return pd.DataFrame(summary)
