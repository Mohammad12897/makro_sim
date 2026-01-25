#core/covariance.py
import pandas as pd
import numpy as np
from sklearn.covariance import LedoitWolf

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
