#  risk_dashboard/core/scenario_engine.py
import pandas as pd
import numpy as np
from matplotlib.pylab import var
import pandas as pd
from risk_dashboard.core.macro_loader import load_macro_data


VARIABLES = [
    "BIP (Mrd USD)",
    "Inflation (%)",
    "Arbeitslosenquote (%)",
    "Zinssatz (%)"
]

def load_base_data():
    df = pd.DataFrame()
    df["date"] = load_macro_data("GDP")["date"]
    df["gdp"] = load_macro_data("GDP")["value"]
    df["cpi"] = load_macro_data("CPIAUCSL")["value"]
    df["unrate"] = load_macro_data("UNRATE")["value"]
    df["fedfunds"] = load_macro_data("FEDFUNDS")["value"]
    return df

SCENARIOS = {
    "Baseline": {"gdp": 0.0, "cpi": 0.0, "unrate": 0.0, "fedfunds": 0.0},
    "Recession": {"gdp": -0.04, "cpi": -0.01, "unrate": 0.02, "fedfunds": -0.01},
    "High Inflation": {"gdp": -0.01, "cpi": 0.04, "unrate": 0.01, "fedfunds": 0.02},
    "Tightening": {"gdp": -0.02, "cpi": -0.01, "unrate": 0.01, "fedfunds": 0.03},
}

def apply_shock(df, shocks):
    df_sim = df.copy()
    for var, shock in shocks.items():
        df_sim[var] = df_sim[var] * (1 + shock)
    return df_sim



def generate_date_range(start="2026-01-01", periods=24, freq="ME"):
    return pd.date_range(start=start, periods=periods, freq=freq)


# ---------------------------------------------------------
# 1. BASELINE-SZENARIO
# ---------------------------------------------------------
def build_baseline_scenario(start="2026-01-01", periods=24):
    dates = generate_date_range(start, periods)

    data = []

    # Beispielhafte Baseline-Pfade (kannst du ersetzen)
    bip = np.linspace(23000, 26000, periods)
    inflation = np.linspace(2.0, 2.2, periods)
    unemployment = np.linspace(4.0, 3.8, periods)
    interest = np.linspace(3.5, 3.0, periods)

    series = [bip, inflation, unemployment, interest]

    for var, values in zip(VARIABLES, series):
        for d, v in zip(dates, values):
            data.append({
                "date": d,
                "variable_Label": var,
                "value": float(v)
            })

    return pd.DataFrame(data)


# ---------------------------------------------------------
# 2. BENUTZERDEFINIERTES SZENARIO
# ---------------------------------------------------------
def build_scenario(
    start="2026-01-01",
    periods=24,
    bip_shock=0.95,
    inflation_shock=1.3,
    unemployment_shock=1.2,
    interest_shock=1.5
):
    """
    Erzeugt ein Szenario basierend auf Schocks.
    Beispiel:
    - bip_shock=0.95 → BIP -5%
    - inflation_shock=1.3 → Inflation +30%
    """

    baseline = build_baseline_scenario(start, periods)
    scenario = baseline.copy()

    shock_map = {
        "BIP (Mrd USD)": bip_shock,
        "Inflation (%)": inflation_shock,
        "Arbeitslosenquote (%)": unemployment_shock,
        "Zinssatz (%)": interest_shock
    }

    scenario["value"] = scenario.apply(
        lambda row: row["value"] * shock_map[row["variable_Label"]],
        axis=1
    )

    return scenario
