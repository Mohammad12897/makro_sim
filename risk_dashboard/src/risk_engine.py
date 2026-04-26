<<<<<<< HEAD
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
=======
# risk_dashboard/src/risk_engine.py

import pandas as pd
from risk_dashboard.src.risk_factors import compute_factor_changes
from risk_dashboard.src.fx_integration import get_fx_forecast


def compute_risk_score(df: pd.DataFrame):
    df = compute_factor_changes(df)
    latest = df.iloc[-1]

    components = {
        "growth_risk": latest["gdp_growth"],
        "inflation_risk": latest["inflation"],
        "rate_risk": latest["interest_rate"],
        "labor_risk": latest["unemployment"],
        "oil_risk": latest["oil_price"],
        "fx_risk": latest["fx_rate"],
    }

>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
    score = sum(components.values()) / len(components)
    return float(score), components
