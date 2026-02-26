#/src/risk_engine.py
import pandas as pd
from .risk_factors import compute_factor_changes
from .fx_integration import get_fx_forecast

def compute_risk_score(df: pd.DataFrame) -> float:
    df = compute_factor_changes(df)
    latest = df.iloc[-1]

    # einfache, gewichtete Beispiel‑Logik
    components = {
        "growth_risk": -latest["gdp_growth"],
        "inflation_risk": latest["inflation"],
        "rate_risk": latest["interest_rate"],
        "labor_risk": latest["unemployment"],
        "pmi_risk": -latest["pmi"],
        "equity_risk": -latest["equity_index_chg"],
        "commodity_risk": latest["commodity_index_chg"],
        "credit_risk": latest["credit_spread"],
        "vol_risk": latest["vix"],
        "fx_risk": abs(get_fx_forecast() - latest["equity_index"])  # Platzhalter
    }

    # einfache Summe / Mittelwert als Score
    score = sum(components.values()) / len(components)
    return float(score), components
