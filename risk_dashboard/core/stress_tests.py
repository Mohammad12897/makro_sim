# risk_dashboard/src/core/stress_tests.py
import numpy as np
import pandas as pd

def apply_shock(value, shock_pct):
    return value * (1 + shock_pct)

def stress_test_fx(fx_forecast, shocks=None):
    if shocks is None:
        shocks = [-0.10, -0.05, 0.05, 0.10]  # ±5%, ±10%

    results = []
    for shock in shocks:
        shocked_value = apply_shock(fx_forecast, shock)
        results.append({
            "shock": f"{shock*100:.0f}%",
            "value": shocked_value
        })

    return pd.DataFrame(results)

def calculate_var(returns, confidence=0.95):
    return np.percentile(returns, (1 - confidence) * 100)