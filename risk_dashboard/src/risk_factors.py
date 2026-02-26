#/src/risk_factors.py
import pandas as pd

def compute_factor_changes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["gdp_growth", "inflation", "interest_rate", "unemployment",
                "pmi", "equity_index", "commodity_index", "credit_spread", "vix"]:
        df[f"{col}_chg"] = df[col].pct_change()
    return df
