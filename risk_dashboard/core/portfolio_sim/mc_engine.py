#core/portfolio_sim/mc_engine.py
# Portfolio-Simulator deaktiviert (Option A)

import pandas as pd

def run_portfolio_mc(*args, **kwargs):
    # Gibt Dummy-Werte zurück, damit kein Unpacking-Fehler entsteht
    return None, None

def compare_portfolios(land, presets, portfolios, years, scenario):
    # Gibt eine leere Tabelle zurück, damit die UI nicht abstürzt
    df = pd.DataFrame(columns=[
        "Portfolio", "Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])
    return df
