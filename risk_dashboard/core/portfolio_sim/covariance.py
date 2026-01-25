#core/portfolio_sim/covariance.py
import pandas as pd
import numpy as np
from sklearn.covariance import LedoitWolf
from core.data_import import load_returns_csv


DATA_PATH = "/content/makro_sim/risk_dashboard/data"

def compute_covariance(df, method="standard"):
    """
    df: DataFrame mit Renditen
    method: standard | ewma | shrinkage
    """

    if method == "standard":
        return df.cov()

    elif method == "ewma":
        lambda_ = 0.94
        cov = df.ewm(alpha=1-lambda_).cov().iloc[-len(df.columns):]
        return cov

    elif method == "shrinkage":
        lw = LedoitWolf().fit(df.values)
        return pd.DataFrame(lw.covariance_, index=df.columns, columns=df.columns)

    else:
        raise ValueError("Unbekannte Methode")


def build_asset_covariance():
    equity_df = load_returns_csv(
        f"{DATA_PATH}/equity_returns.csv",
        expected_assets=["USA", "Germany", "India", "Brazil", "SouthAfrica"]
    )
    bond_df = load_returns_csv(
        f"{DATA_PATH}/bond_returns.csv",
        expected_assets=["USA", "Germany", "India", "Brazil", "SouthAfrica"]
    )
    gold_df = load_returns_csv(
        f"{DATA_PATH}/gold_returns.csv",
        expected_assets=["Gold"]
    )

    equity_vol = equity_df.mean(axis=1).std()
    bond_vol = bond_df.mean(axis=1).std()
    gold_vol = gold_df["Gold"].std()

    corr = np.array([
        [1.0, 0.25, 0.10],
        [0.25, 1.0, 0.05],
        [0.10, 0.05, 1.0],
    ])

    vols = np.array([equity_vol, bond_vol, gold_vol])
    cov = np.outer(vols, vols) * corr

    return pd.DataFrame(
        cov,
        index=["equity", "bonds", "gold"],
        columns=["equity", "bonds", "gold"],
    )
