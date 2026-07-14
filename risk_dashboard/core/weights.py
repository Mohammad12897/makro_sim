import pandas as pd

def compute_abs_weights(df: pd.DataFrame, portfolio_value: float) -> pd.DataFrame:
    df = df.copy()
    # Stelle sicher, dass 'market_value' existiert; sonst 0.0 setzen
    if "market_value" not in df.columns:
        df["market_value"] = 0.0
    # Vektorisiertes Rechnen; falls portfolio_value == 0, setze 0.0
    if portfolio_value and portfolio_value > 0:
        df["abs_weight"] = df["market_value"] / float(portfolio_value)
    else:
        df["abs_weight"] = 0.0
    return df
