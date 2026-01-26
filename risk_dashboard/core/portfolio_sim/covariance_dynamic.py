#core/portfolio_sim/covariance_dynamic.py
import numpy as np
import pandas as pd

def dynamic_covariance(base_cov, scenario):
    cov = base_cov.copy()

    if scenario == "Krise":
        cov *= 1.5

    elif scenario == "Zinsanstieg":
        cov.loc["equity", "bonds"] *= -0.5
        cov.loc["bonds", "equity"] *= -0.5

    elif scenario == "Ölpreisschock":
        cov.loc["equity", "gold"] *= -0.5
        cov.loc["gold", "equity"] *= -0.5
        cov.loc["bonds", "gold"] *= 1.2
        cov.loc["gold", "bonds"] *= 1.2

    return cov
