# core/regime_model.py
import pandas as pd
from typing import Union
import yfinance as yf
import streamlit as st


REGIMES = [
    "Krise",
    "Rezession",
    "Stagnation",
    "Expansion",
    "Boom"
]

def classify_regime_from_score(score: float) -> str:
    """
    Mappt einen kontinuierlichen Risiko-/Makro-Score auf ein diskretes Regime.
    Score kann z.B. aus deinem Makro-Risiko-Modell kommen.
    """
    if score <= -1.5:
        return "Krise"
    elif score <= -0.5:
        return "Rezession"
    elif score <= 0.5:
        return "Stagnation"
    elif score <= 1.5:
        return "Expansion"
    else:
        return "Boom"



def build_regime_timeline(score_series: Union[pd.Series, pd.DataFrame]) -> pd.DataFrame:
    """
    Erwartet eine Serie mit Index = Datum und Werten = Score
    oder ein DataFrame mit Spalte 'risk_score'.
    Gibt ein DataFrame mit Spalten: ['date', 'risk_score', 'regime'] zurück.
    """
    if isinstance(score_series, pd.DataFrame):
        if "risk_score" not in score_series.columns:
            raise ValueError("DataFrame muss Spalte 'risk_score' enthalten.")
        s = score_series["risk_score"].copy()
    else:
        s = score_series.copy()

    s = s.dropna()
    df = s.to_frame(name="risk_score").reset_index().rename(columns={"index": "date"})

    df["regime"] = df["risk_score"].apply(classify_regime_from_score)
    return df

def compute_regime_transition_matrix(regime_df: pd.DataFrame) -> pd.DataFrame:
    """
    Erwartet DataFrame mit Spalte 'regime' (z.B. Output von build_regime_timeline).
    Gibt eine normalisierte Transitionsmatrix zurück.
    """
    if "regime" not in regime_df.columns:
        raise ValueError("regime_df muss Spalte 'regime' enthalten.")

    reg_series = regime_df["regime"].astype("category")
    trans = pd.crosstab(
        reg_series.shift(1),
        reg_series,
        normalize="index"
    ).fillna(0.0)

    trans.index.name = "From"
    trans.columns.name = "To"
    return trans

def next_regime_distribution(current_regime: str, trans_matrix: pd.DataFrame) -> pd.Series:
    """
    Gibt die Wahrscheinlichkeitsverteilung für das nächste Regime zurück.
    """
    if current_regime not in trans_matrix.index:
        raise ValueError(f"Unbekanntes Regime: {current_regime}")

    return trans_matrix.loc[current_regime]

