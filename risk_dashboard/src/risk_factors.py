<<<<<<< HEAD
#/src/risk_factors.py
=======
# risk_dashboard/src/risk_factors.py
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
import pandas as pd

def compute_factor_changes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["gdp_growth", "inflation", "interest_rate", "unemployment",
<<<<<<< HEAD
                "pmi", "equity_index", "commodity_index", "credit_spread", "vix"]:
=======
                "oil_price", "fx_rate"]:
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
        df[f"{col}_chg"] = df[col].pct_change()
    return df
