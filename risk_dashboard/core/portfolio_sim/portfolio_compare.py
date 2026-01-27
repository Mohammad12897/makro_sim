#core/portfolio_sim/portfolio_compare.py
import pandas as pd

def run_portfolio_mc(*args, **kwargs):
    # Gibt Dummy-Werte zurück, damit nichts abstürzt
    return None, None

def compare_portfolios(land, presets, portfolios, years, scenario):
    # Gibt eine leere Tabelle zurück, statt abzustürzen
    df = pd.DataFrame(columns=[
        "Portfolio", "Mean", "Volatilität", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])
    return df
