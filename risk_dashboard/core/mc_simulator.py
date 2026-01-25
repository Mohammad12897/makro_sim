# core/mc_simulator.py
import numpy as np
import pandas as pd

def multi_period_mc(
    weights,
    mu,
    cov,
    years=10,
    n_paths=5000,
    rebalancing=True,
    shock_fn=None,
    seed=42
):
    """
    weights: np.array([w_equity, w_bond, w_gold])
    mu: dict mit erwarteten Renditen
    cov: Kovarianzmatrix
    shock_fn: Funktion, die (mu, cov, year) -> (mu_new, cov_new) zurückgibt
    """

    rng = np.random.default_rng(seed)
    assets = list(mu.keys())
    mu_vec = np.array([mu[a] for a in assets])
    cov_mat = cov.values

    results = np.zeros((n_paths, years))

    for path in range(n_paths):
        w = weights.copy()
        mu_t = mu_vec.copy()
        cov_t = cov_mat.copy()

        for t in range(years):

            # Szenario-Schock pro Jahr
            if shock_fn:
                mu_dict = {a: mu_t[i] for i, a in enumerate(assets)}
                mu_dict, cov_t = shock_fn(mu_dict, cov_t, t)
                mu_t = np.array([mu_dict[a] for a in assets])

            # Jahresrendite simulieren
            ret = rng.multivariate_normal(mu_t, cov_t)
            portfolio_ret = np.dot(w, ret)
            results[path, t] = portfolio_ret

            # Rebalancing
            if rebalancing:
                w = weights.copy()

    return {
        "paths": results,
        "mean": results.mean(axis=0),
        "var95": np.percentile(results, 5, axis=0),
        "cvar95": results[results <= np.percentile(results, 5)].mean(),
        "terminal_distribution": results.sum(axis=1)
    }


def summarize_paths(results):
    """
    results: dict von multi_period_mc
    Gibt DataFrame mit mean, var95, cvar95 pro Jahr zurück.
    """
    years = results["paths"].shape[1]
    df = pd.DataFrame({
        "year": np.arange(1, years + 1),
        "mean": results["mean"],
        "var95": results["var95"],
    })
    return df
