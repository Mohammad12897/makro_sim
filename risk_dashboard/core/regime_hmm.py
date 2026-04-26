import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import yfinance as yf
import streamlit as st




def fit_hmm_regimes(
    feature_df: pd.DataFrame,
    n_states: int = 3,
    covariance_type: str = "full",
    n_iter: int = 200,
    random_state: int = 42
):
    # Nur numerische Features
    df_num = feature_df.select_dtypes(include=["float", "int"]).copy()

    # NaNs entfernen
    df_num = df_num.dropna()

    if len(df_num) < 10:
        raise ValueError("Zu wenige Daten für HMM nach Entfernen von NaNs.")

    X = df_num.values

    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=n_iter,
        random_state=random_state
    )

    model.fit(X)
    hidden_states = model.predict(X)

    regime_df = df_num.copy()
    regime_df["hmm_state"] = hidden_states

    return model, regime_df



def map_hmm_states_to_labels(regime_df: pd.DataFrame):
    grouped = regime_df.groupby("hmm_state").mean(numeric_only=True)
    variances = grouped.var()
    best_col = variances.idxmax()
    order = grouped[best_col].sort_values().index.tolist()

    labels = ["Krise", "Rezession", "Stagnation", "Expansion", "Boom"]
    label_map = {state: labels[i] for i, state in enumerate(order)}

    regime_df["regime_label"] = regime_df["hmm_state"].map(label_map)
    return regime_df, label_map, best_col
